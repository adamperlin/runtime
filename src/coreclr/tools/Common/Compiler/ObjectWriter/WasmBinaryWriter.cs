// Licensed to the .NET Foundation under one or more agreements.
// The .NET Foundation licenses this file to you under the MIT license.

using System;
using System.Diagnostics;
using System.Collections.Generic;

namespace ILCompiler.ObjectWriter
{
    /// <summary>
    /// A writer that can either measure or write WASM binary data.
    /// When buffer is empty, operates in measure-only mode.
    /// </summary>
    public ref struct WasmBinaryWriter
    {
        private readonly Span<byte> _buffer;
        private int _position;

        public WasmBinaryWriter(Span<byte> buffer)
        {
            _buffer = buffer;
            _position = 0;
        }

        /// <summary>
        /// Returns true if the writer is in measure-only mode (no actual writes).
        /// </summary>
        public readonly bool IsMeasuring => _buffer.IsEmpty;

        /// <summary>
        /// Gets the number of bytes written (or that would be written in measure mode).
        /// </summary>
        public readonly int BytesWritten => _position;

        public void WriteByte(byte value)
        {
            if (!IsMeasuring)
            {
                _buffer[_position] = value;
            }
            _position++;
        }

        public void WriteBytes(ReadOnlySpan<byte> bytes)
        {
            if (!IsMeasuring)
            {
                bytes.CopyTo(_buffer.Slice(_position));
            }
            _position += bytes.Length;
        }

        public void WriteULEB128(ulong value)
        {
            if (IsMeasuring)
            {
                _position += (int)DwarfHelper.SizeOfULEB128(value);
            }
            else
            {
                _position += DwarfHelper.WriteULEB128(_buffer.Slice(_position), value);
            }
        }

        public void WriteSLEB128(long value)
        {
            if (IsMeasuring)
            {
                _position += (int)DwarfHelper.SizeOfSLEB128(value);
            }
            else
            {
                _position += DwarfHelper.WriteSLEB128(_buffer.Slice(_position), value);
            }
        }
    }

    public interface IWasmEncodable
    {
        public void Encode(ref WasmBinaryWriter writer);
    }


    /// <summary>
    /// Extension methods for <see cref="IWasmEncodable"/>.
    /// </summary>
    public static class WasmEncodableExtensions
    {
        /// <summary>
        /// Gets the encoded size in bytes without actually writing.
        /// </summary>
        public static int GetEncodedSize(this IWasmEncodable encodable)
        {
            var writer = new WasmBinaryWriter(Span<byte>.Empty);
            encodable.Encode(ref writer);
            return writer.BytesWritten;
        }

        /// <summary>
        /// Encodes to the buffer and returns the number of bytes written.
        /// </summary>
        public static int EncodeTo(this IWasmEncodable encodable, Span<byte> buffer)
        {
            WasmBinaryWriter writer = new WasmBinaryWriter(buffer);
            encodable.Encode(ref writer);
            Debug.Assert(writer.BytesWritten <= buffer.Length, "Buffer overflow during encoding");
            return writer.BytesWritten;
        }
    }
}
