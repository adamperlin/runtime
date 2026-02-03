// Licensed to the .NET Foundation under one or more agreements.
// The .NET Foundation licenses this file to you under the MIT license.

using System;
using System.Diagnostics;
using System.Linq;
using System.Collections.Generic;

namespace ILCompiler.ObjectWriter
{
    public enum WasmSectionType
    {
        Custom = 0,
        Type = 1,
        Import = 2,
        Function = 3,
        Table = 4,
        Memory = 5,
        Global = 6,
        Export = 7,
        Start = 8,
        Element = 9,
        Code = 10,
        Data = 11,
        DataCount = 12,
        Tag = 13,
    }

    public static class PlaceholderValues
    {
        // Wasm function signature for (func (params i32) (result i32))
        public static WasmFuncType CreateWasmFunc_i32_i32()
        {
            return new WasmFuncType(
                paramTypes: new([WasmValueType.I32]),
                returnTypes: new([WasmValueType.I32])
            );
        }
    }

    // For now, we only encode Wasm numeric value types.
    // These are encoded as a single byte. However,
    // not all value types can be encoded this way.
    // For example, reference types (see https://webassembly.github.io/spec/core/binary/types.html#reference-types)
    // require a more complex encoding.
    public enum WasmValueType : byte
    {
        I32 = 0x7F,
        I64 = 0x7E,
        F32 = 0x7D,
        F64 = 0x7C
    }

    public enum WasmMutabilityType : byte
    {
        Const = 0x00,
        Mut = 0x01
    }

    public static class WasmValueTypeExtensions
    {
        public static string ToTypeString(this WasmValueType valueType)
        {
            return valueType switch
            {
                WasmValueType.I32 => "i32",
                WasmValueType.I64 => "i64",
                WasmValueType.F32 => "f32",
                WasmValueType.F64 => "f64",
                _ => "unknown",
            };
        }
    }

#nullable enable
    public readonly struct WasmResultType : IEquatable<WasmResultType>
    {
        private readonly WasmValueType[] _types;
        public ReadOnlySpan<WasmValueType> Types => _types;

        /// <summary>
        /// Initializes a new instance of the WasmResultType class with the specified value types.
        /// </summary>
        /// <param name="types">An array of WasmValueType elements representing the types included in the result. If null, an empty array is
        /// used.</param>
        public WasmResultType(WasmValueType[]? types)
        {
            _types = types ?? Array.Empty<WasmValueType>();
        }

        public bool Equals(WasmResultType other) => Types.SequenceEqual(other.Types);
        public override bool Equals(object? obj)
        {
            return obj is WasmResultType other && Equals(other);
        }

        public override int GetHashCode()
        {
            if (_types == null || _types.Length == 0)
                return 0;

            int code = _types[0].GetHashCode();
            for (int i = 1; i < _types.Length; i++)
            {
                code = HashCode.Combine(code, _types[i].GetHashCode());
            }

            return code;
        }

        public int Encode(ref WasmBinaryWriter writer)
        {
            writer.WriteULEB128((ulong)_types.Length);
            for (int i = 0; i < _types.Length; i++)
            {
                writer.WriteByte((byte)_types[i]);
            }

            return writer.BytesWritten;
        }
    }

    public static class WasmResultTypeExtensions
    {
        public static string ToTypeListString(this WasmResultType result)
        {
            return string.Join(" ", result.Types.ToArray().Select(t => t.ToTypeString()));
        }
    }

    public struct WasmFuncType : IEquatable<WasmFuncType>, IWasmEncodable
    {
        private readonly WasmResultType _params;
        private readonly WasmResultType _returns;

        public WasmFuncType(WasmResultType paramTypes, WasmResultType returnTypes)
        {
            _params = paramTypes;
            _returns = returnTypes;
        }

        public readonly void Encode(ref WasmBinaryWriter writer)
        {
            writer.WriteByte(0x60); // function type indicator

            _params.Encode(ref writer);
            _returns.Encode(ref writer);
        }

        public bool Equals(WasmFuncType other)
        {
            return _params.Equals(other._params) && _returns.Equals(other._returns);
        }

        public override bool Equals(object? obj)
        {
            return obj is WasmFuncType other && Equals(other);
        }

        public override int GetHashCode()
        {
            return HashCode.Combine(_params.GetHashCode(), _returns.GetHashCode());
        }

        public override string ToString()
        {
            string paramList = _params.ToTypeListString();
            string returnList = _returns.ToTypeListString();

            if (string.IsNullOrEmpty(returnList))
                return $"(func (param {paramList}))";
            return $"(func (param {paramList}) (result {returnList}))";
        }
    }

    public abstract class WasmImportType : IWasmEncodable
    {
        public abstract void Encode(ref WasmBinaryWriter writer);
    }

    public enum WasmExternalKind : byte
    {
        Function = 0x00,
        Table = 0x01,
        Memory = 0x02,
        Global = 0x03,
        Tag = 0x04,
        Count = 0x05 // Not actually part of the spec; used for counting kinds
    }

    public class WasmGlobalType : WasmImportType
    {
        WasmValueType _valueType;
        WasmMutabilityType _mutability;

        public WasmGlobalType(WasmValueType valueType, WasmMutabilityType mutability)
        {
            _valueType = valueType;
            _mutability = mutability;
        }

        public override void Encode(ref WasmBinaryWriter writer)
        {
            writer.WriteByte((byte)_valueType);
            writer.WriteByte((byte)_mutability);
        }
    }

    public enum WasmLimitType : byte
    {
        HasMin = 0x00,
        HasMinAndMax = 0x01
    }
  
    public class WasmMemoryType : WasmImportType
    {
        WasmLimitType _limitType;
        uint _min;
        uint? _max;

        public WasmMemoryType(WasmLimitType limitType, uint min, uint? max = null)
        {
            if (limitType == WasmLimitType.HasMinAndMax && !max.HasValue)
            {
                throw new ArgumentException("Max must be provided when LimitType is HasMinAndMax");
            }

            _limitType = limitType;
            _min = min;
            _max = max;
        }

        public override void Encode(ref WasmBinaryWriter writer)
        {
            writer.WriteByte((byte)_limitType);
            writer.WriteULEB128(_min);
            if (_limitType == WasmLimitType.HasMinAndMax)
            {
                writer.WriteULEB128(_max!.Value);
            }
        }
    }

    public class WasmImport : IWasmEncodable
    {
        public readonly string Module;
        public readonly string Name;
        public readonly WasmExternalKind Kind;
        public readonly int? Index;
        public readonly WasmImportType Import;

        public WasmImport(string module, string name, WasmExternalKind kind, WasmImportType import, int? index = null)
        {
            Module = module;
            Name = name;
            Kind = kind;
            Import = import;
            Index = index;
        }

        public void Encode(ref WasmBinaryWriter writer) => Import.Encode(ref writer);
    }
}
