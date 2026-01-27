// Licensed to the .NET Foundation under one or more agreements.
// The .NET Foundation licenses this file to you under the MIT license.

import type { CharPtr, VfsAsset, VoidPtr, VoidPtrPtr, WasmAsset } from "./types";
import { _ems_ } from "../../../libs/Common/JavaScript/ems-ambient";

import { dotnetAssert, dotnetLogger } from "./cross-module";
import { ENVIRONMENT_IS_WEB } from "./per-module";

let wasmMemory: WebAssembly.Memory = undefined as any;
let wasmMainTable: WebAssembly.Table = undefined as any;
const hasInstantiateStreaming = typeof WebAssembly !== "undefined" && typeof WebAssembly.instantiateStreaming === "function";
const loadedAssemblies: Map<string, { ptr: number, length: number }> = new Map();
const loadedR2R: Map<string, WebAssembly.Instance> = new Map();

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function registerPdbBytes(bytes: Uint8Array, asset: { name: string, virtualPath: string }) {
    // WASM-TODO: https://github.com/dotnet/runtime/issues/122921
}

export function registerDllBytes(bytes: Uint8Array, asset: { name: string, virtualPath: string }) {
    const sp = _ems_.stackSave();
    try {
        const sizeOfPtr = 4;
        const ptrPtr = _ems_.stackAlloc(sizeOfPtr);
        if (_ems_._posix_memalign(ptrPtr as any, 16, bytes.length)) {
            throw new Error("posix_memalign failed");
        }

        const ptr = _ems_.HEAPU32[ptrPtr as any >>> 2];
        _ems_.HEAPU8.set(bytes, ptr >>> 0);
        loadedAssemblies.set(asset.virtualPath, { ptr, length: bytes.length });
        if (!asset.virtualPath.startsWith("/")) {
            loadedAssemblies.set("/" + asset.virtualPath, { ptr, length: bytes.length });
        }
    } finally {
        _ems_.stackRestore(sp);
    }
}

export function BrowserHost_ExternalAssemblyProbe(pathPtr: CharPtr, outDataStartPtr: VoidPtrPtr, outSize: VoidPtr) {
    const path = _ems_.UTF8ToString(pathPtr);
    const assembly = loadedAssemblies.get(path);
    if (assembly) {
        _ems_.HEAPU32[outDataStartPtr as any >>> 2] = assembly.ptr;
        // int64_t target
        _ems_.HEAPU32[outSize as any >>> 2] = assembly.length;
        _ems_.HEAPU32[((outSize as any) + 4) >>> 2] = 0;
        return true;
    }
    _ems_.dotnetLogger.debug(`Assembly not found: '${path}'`);
    _ems_.HEAPU32[outDataStartPtr as any >>> 2] = 0;
    _ems_.HEAPU32[outSize as any >>> 2] = 0;
    _ems_.HEAPU32[((outSize as any) + 4) >>> 2] = 0;
    return false;
}

export function loadIcuData(bytes: Uint8Array) {
    const sp = _ems_.stackSave();
    try {
        const sizeOfPtr = 4;
        const ptrPtr = _ems_.stackAlloc(sizeOfPtr);
        if (_ems_._posix_memalign(ptrPtr as any, 16, bytes.length)) {
            throw new Error("posix_memalign failed for ICU data");
        }

        const ptr = _ems_.HEAPU32[ptrPtr as any >>> 2];
        _ems_.HEAPU8.set(bytes, ptr >>> 0);

        const result = _ems_._wasm_load_icu_data(ptr as unknown as VoidPtr);
        if (!result) {
            throw new Error("Failed to initialize ICU data");
        }
    } finally {
        _ems_.stackRestore(sp);
    }
}

export function installVfsFile(bytes: Uint8Array, asset: VfsAsset) {
    const virtualName: string = typeof (asset.virtualPath) === "string"
        ? asset.virtualPath
        : asset.name;
    const lastSlash = virtualName.lastIndexOf("/");
    let parentDirectory = (lastSlash > 0)
        ? virtualName.substring(0, lastSlash)
        : null;
    let fileName = (lastSlash > 0)
        ? virtualName.substring(lastSlash + 1)
        : virtualName;
    if (fileName.startsWith("/"))
        fileName = fileName.substring(1);
    if (parentDirectory) {
        if (!parentDirectory.startsWith("/"))
            parentDirectory = "/" + parentDirectory;

        if (parentDirectory.startsWith("/managed")) {
            throw new Error("Cannot create files under /managed virtual directory as it is reserved for NodeFS mounting");
        }

        _ems_.dotnetLogger.debug(`Creating directory '${parentDirectory}'`);

        _ems_.FS.createPath(
            "/", parentDirectory, true, true // fixme: should canWrite be false?
        );
    } else {
        parentDirectory = "/";
    }

    _ems_.dotnetLogger.debug(`Creating file '${fileName}' in directory '${parentDirectory}'`);

    _ems_.FS.createDataFile(
        parentDirectory, fileName,
        bytes, true /* canRead */, true /* canWrite */, true /* canOwn */
    );
}

export async function instantiateR2RModule(asset: WasmAsset, r2rPromise: Promise<Response>): Promise<void> {
    const importsTable = new WebAssembly.Table({ initial: 1, element: "anyfunc" });
    /*
    importsTable.set(0, _ems_._malloc);
    importsTable.set(1, wasmMainTable.get(0));
    importsTable.set(2, () => "any JS function can be here");
    */

    const imports: WebAssembly.Imports = {
        // TODO-WASM: match the imports needed by R2R modules
        env: {
            memory: wasmMemory,
            // TODO-WASM: match the imports needed by R2R modules
            table: importsTable,
        }
    };

    const { instance } = await instantiateWasm(r2rPromise, imports, !!asset.buffer, false);

    loadedR2R.set(asset.name, instance);
}

export async function instantiateWasm(wasmPromise: Promise<Response>, imports: WebAssembly.Imports, isStreaming: boolean, isMainModule: boolean): Promise<{ instance: WebAssembly.Instance; module: WebAssembly.Module; }> {
    let instance: WebAssembly.Instance;
    let module: WebAssembly.Module;
    if (!hasInstantiateStreaming || !isStreaming) {
        const res = await checkResponseOk(wasmPromise);
        const data = await res.arrayBuffer();
        module = await WebAssembly.compile(data);
        instance = await WebAssembly.instantiate(module, imports);
    } else {
        const instantiated = await WebAssembly.instantiateStreaming(wasmPromise, imports);
        await checkResponseOk(wasmPromise);
        instance = instantiated.instance;
        module = instantiated.module;
    }
    if (isMainModule) {
        wasmMemory = instance.exports.memory as WebAssembly.Memory;
        wasmMainTable = instance.exports.__indirect_function_table as WebAssembly.Table;
    }
    return { instance, module };
}

async function checkResponseOk(wasmPromise: Promise<Response> | undefined): Promise<Response> {
    dotnetAssert.check(wasmPromise, "WASM binary promise was not initialized");
    const res = await wasmPromise;
    if (!res || res.ok === false) {
        throw new Error(`Failed to load WebAssembly module. HTTP status: ${res?.status} ${res?.statusText}`);
    }
    const contentType = res.headers && res.headers.get ? res.headers.get("Content-Type") : undefined;
    if (ENVIRONMENT_IS_WEB && contentType !== "application/wasm") {
        dotnetLogger.warn("WebAssembly resource does not have the expected content type \"application/wasm\", so falling back to slower ArrayBuffer instantiation.");
    }
    return res;
}

export function BrowserHost_ExternalR2RProbe(libraryName: CharPtr, entryPointName: CharPtr): VoidPtr {
    const libraryNameStr = _ems_.UTF8ToString(libraryName);
    const entryPointNameStr = _ems_.UTF8ToString(entryPointName);
    const instance = loadedR2R.get(libraryNameStr);
    if (!instance) {
        _ems_.dotnetLogger.debug(`R2R instance not found: '${libraryNameStr}'`);
        return 0 as any;
    }
    const exportFunc = instance.exports[entryPointNameStr];
    if (typeof exportFunc !== "function") {
        _ems_.dotnetLogger.debug(`R2R export not found: '${entryPointNameStr}' in '${libraryNameStr}'`);
        return 0 as any;
    }

    const funcIndex = wasmMainTable.length;
    wasmMainTable.grow(1);
    wasmMainTable.set(funcIndex, exportFunc);

    return funcIndex as any;
}


