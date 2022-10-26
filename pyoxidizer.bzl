def make_exe():
    dist = default_python_distribution(python_version="3.9")
    policy = dist.make_python_packaging_policy()

    python_config = dist.make_python_interpreter_config()

    # Make the embedded interpreter behave like a `python` process.
    python_config.config_profile = "python"

    python_config.filesystem_importer = True

    # Run a Python module as __main__ when the interpreter starts.
    python_config.run_module = "spacestream"

    exe = dist.to_python_executable(
        name="space-stream",
        packaging_policy=policy,
        config=python_config,
    )

    exe.windows_runtime_dlls_mode = "when-present"

    # Copy Windows runtime DLLs next to the build executable and error if this
    # cannot be done.
    # exe.windows_runtime_dlls_mode = "always"

    # Make the executable a console application on Windows.
    exe.windows_subsystem = "console"

    # Make the executable a non-console application on Windows.
    # exe.windows_subsystem = "windows"

    exe.add_python_resources(exe.pip_install(["-r", "requirements.txt"]))

    # Filter all resources collected so far through a filter of names
    # in a file.
    #exe.filter_resources_from_files(files=["/path/to/filter-file"])

    # Return our `PythonExecutable` instance so it can be built and
    # referenced by other consumers of this target.
    return exe

def make_embedded_resources(exe):
    return exe.to_embedded_resources()

def make_install(exe):
    # Create an object that represents our installed application file layout.
    files = FileManifest()

    # Add the generated executable to our install layout in the root directory.
    files.add_python_resource(".", exe)

    return files

def make_msi(exe):
    # See the full docs for more. But this will convert your Python executable
    # into a `WiXMSIBuilder` Starlark type, which will be converted to a Windows
    # .msi installer when it is built.
    return exe.to_wix_msi_builder(
        # Simple identifier of your app.
        "myapp",
        # The name of your application.
        "My Application",
        # The version of your application.
        "1.0",
        # The author/manufacturer of your application.
        "Alice Jones"
    )


# Dynamically enable automatic code signing.
def register_code_signers():
    # You will need to run with `pyoxidizer build --var ENABLE_CODE_SIGNING 1` for
    # this if block to be evaluated.
    if not VARS.get("ENABLE_CODE_SIGNING"):
        return

    # Use a code signing certificate in a .pfx/.p12 file, prompting the
    # user for its path and password to open.
    # pfx_path = prompt_input("path to code signing certificate file")
    # pfx_password = prompt_password(
    #     "password for code signing certificate file",
    #     confirm = True
    # )
    # signer = code_signer_from_pfx_file(pfx_path, pfx_password)

    # Use a code signing certificate in the Windows certificate store, specified
    # by its SHA-1 thumbprint. (This allows you to use YubiKeys and other
    # hardware tokens if they speak to the Windows certificate APIs.)
    # sha1_thumbprint = prompt_input(
    #     "SHA-1 thumbprint of code signing certificate in Windows store"
    # )
    # signer = code_signer_from_windows_store_sha1_thumbprint(sha1_thumbprint)

    # Choose a code signing certificate automatically from the Windows
    # certificate store.
    # signer = code_signer_from_windows_store_auto()

    # Activate your signer so it gets called automatically.
    # signer.activate()


# Call our function to set up automatic code signers.
register_code_signers()

# Tell PyOxidizer about the build targets defined above.
register_target("exe", make_exe)
register_target("resources", make_embedded_resources, depends=["exe"], default_build_script=True)
register_target("install", make_install, depends=["exe"], default=True)
register_target("msi_installer", make_msi, depends=["exe"])

# Resolve whatever targets the invoker of this configuration file is requesting
# be resolved.
resolve_targets()
