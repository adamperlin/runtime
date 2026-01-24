// Licensed to the .NET Foundation under one or more agreements.
// The .NET Foundation licenses this file to you under the MIT license.

using System;
using System.Runtime.InteropServices.JavaScript;
using System.Runtime.InteropServices;
using System.Threading.Tasks;

namespace Sample
{
    public partial class Test
    {
        public static Task<int> Main(string[] args)
        {
            int result = TwoInts(1024,20, 22,0);
            if (result != 42)
            {
                throw new Exception($"Expected 42, got {result}");
            }
            Console.WriteLine("R2R test passed");
            return Task.FromResult(0);
        }

        [LibraryImport("R2R.test-module", EntryPoint = "wasm_test_Program__addTwoInts")]
        internal static partial int TwoInts(IntPtr sp, int a, int b, IntPtr pep);
    }
}
