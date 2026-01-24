// Licensed to the .NET Foundation under one or more agreements.
// The .NET Foundation licenses this file to you under the MIT license.

import { dotnet, exit } from './_framework/dotnet.js'

try {
    await dotnet
        .withConfig({
            resources: {
                coreR2R: [{
                    name: "test-module",
                    resolvedUrl: "../test-module.wasm"
                }]
            }
        })
        .withConfig({ appendElementOnExit: true, exitOnUnhandledError: true, forwardConsole: true, logExitCode: true })
        .create();

    await dotnet.runMainAndExit();
}
catch (err) {
    exit(2, err);
}