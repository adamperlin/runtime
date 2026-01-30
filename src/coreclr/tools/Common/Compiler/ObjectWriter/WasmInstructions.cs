// Licensed to the .NET Foundation under one or more agreements.
// The .NET Foundation licenses this file to you under the MIT license.

using System;
using System.Diagnostics;

// This namespace implements encodings for certain Wasm expressions (instructions)
// which are used in the object writer.  
// For now, these instructions are only used for constructing constant expressions
// to calculate placements for data segments based on imported globals. 
namespace ILCompiler.ObjectWriter.WasmInstructions
{
    public enum WasmExprKind
    {
        I32Const = 0x41,
        I64Const = 0x42,
        GlobalGet = 0x23,
        I32Add = 0x6A,
    }

    public static class WasmExprKindExtensions
    {
        public static bool IsConstExpr(this WasmExprKind kind)
        {
            return kind == WasmExprKind.I32Const || kind == WasmExprKind.I64Const;
        }

        public static bool IsBinaryExpr(this WasmExprKind kind)
        {
            return kind == WasmExprKind.I32Add;
        }

        public static bool IsGlobalVarExpr(this WasmExprKind kind)
        {
            return kind == WasmExprKind.GlobalGet;
        }
    }

    // Represents a group of Wasm instructions (expressions) which 
    // form a complete expression ending with the 'end' opcode.
    class WasmInstructionGroup : IWasmEncodable
    {
        readonly WasmExpr[] _wasmExprs;
        public WasmInstructionGroup(WasmExpr[] wasmExprs)
        {
            _wasmExprs = wasmExprs;
        }

        public void Encode(ref WasmBinaryWriter writer)
        {
            foreach (var expr in _wasmExprs)
            {
                expr.Encode(ref writer);
            }
            writer.WriteByte(0x0B); // end opcode
        }
    }

    public abstract class WasmExpr : IWasmEncodable
    {
        WasmExprKind _kind;
        public WasmExpr(WasmExprKind kind)
        {
            _kind = kind;
        }

        public virtual void Encode(ref WasmBinaryWriter writer)
        {
            writer.WriteByte((byte)_kind);
        }
    }

    // Represents a constant expression (e.g., (i32.const <value>))
    class WasmConstExpr : WasmExpr
    {
        long ConstValue;

        public WasmConstExpr(WasmExprKind kind, long value) : base(kind)
        {
            if (kind == WasmExprKind.I32Const)
            {
                ArgumentOutOfRangeException.ThrowIfGreaterThan(value, int.MaxValue);
                ArgumentOutOfRangeException.ThrowIfLessThan(value, int.MinValue);
            }

            ConstValue = value;
        }

        public override void Encode(ref WasmBinaryWriter writer)
        {
            base.Encode(ref writer);
            writer.WriteSLEB128(ConstValue);
        }
    }

    // Represents a global variable expression (e.g., (global.get <index))
    class WasmGlobalVarExpr : WasmExpr
    {
        public readonly int GlobalIndex;
        public WasmGlobalVarExpr(WasmExprKind kind, int globalIndex) : base(kind)
        {
            Debug.Assert(globalIndex >= 0);
            Debug.Assert(kind.IsGlobalVarExpr());
            GlobalIndex = globalIndex;
        }

        public override void Encode(ref WasmBinaryWriter writer)
        {
            base.Encode(ref writer);
            writer.WriteULEB128((uint)GlobalIndex);
        }
    }

    // Represents a binary expression (e.g., i32.add)
    class WasmBinaryExpr : WasmExpr
    {
        public WasmBinaryExpr(WasmExprKind kind) : base(kind)
        {
            Debug.Assert(kind.IsBinaryExpr());
        }

        // base class defaults are sufficient as the base class encodes just the opcode
    }

    // ************************************************
    // Simple DSL wrapper for creating Wasm expressions
    // ************************************************
    static class Global
    {
        public static WasmExpr Get(int index)
        {
            return new WasmGlobalVarExpr(WasmExprKind.GlobalGet, index);
        }
    }

    static class I32
    {
        public static WasmExpr Const(long value)
        {
            return new WasmConstExpr(WasmExprKind.I32Const, value);
        }

        public static WasmExpr Add => new WasmBinaryExpr(WasmExprKind.I32Add);
    }
}
