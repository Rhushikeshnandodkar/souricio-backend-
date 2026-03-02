"""
Run script for the FastAPI application.
This is a convenience script to run the application using uvicorn.
"""
import os
import uvicorn

# Set environment variables for WeasyPrint on macOS
# These are needed for WeasyPrint to find system libraries installed via Homebrew
if os.name == 'posix':  # Unix-like systems (macOS, Linux)
    homebrew_prefix = "/opt/homebrew"  # Default for Apple Silicon Macs
    if not os.path.exists(homebrew_prefix):
        homebrew_prefix = "/usr/local"  # Fallback for Intel Macs
    
    pkg_config_path = f"{homebrew_prefix}/lib/pkgconfig"
    lib_path = f"{homebrew_prefix}/lib"
    
    # Add to PKG_CONFIG_PATH if it exists
    if os.path.exists(pkg_config_path):
        current_pkg_config = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = f"{pkg_config_path}:{current_pkg_config}" if current_pkg_config else pkg_config_path
    
    # Add to DYLD_LIBRARY_PATH (macOS) or LD_LIBRARY_PATH (Linux)
    if os.path.exists(lib_path):
        if os.uname().sysname == "Darwin":  # macOS
            current_dyld = os.environ.get("DYLD_LIBRARY_PATH", "")
            os.environ["DYLD_LIBRARY_PATH"] = f"{lib_path}:{current_dyld}" if current_dyld else lib_path
        else:  # Linux
            current_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{current_ld}" if current_ld else lib_path
    
    # Handle libffi (keg-only package) - needed for WeasyPrint
    libffi_lib = f"{homebrew_prefix}/opt/libffi/lib"
    libffi_include = f"{homebrew_prefix}/opt/libffi/include"
    if os.path.exists(libffi_lib):
        current_ldflags = os.environ.get("LDFLAGS", "")
        os.environ["LDFLAGS"] = f"-L{libffi_lib} {current_ldflags}".strip()
        current_dyld = os.environ.get("DYLD_LIBRARY_PATH", "")
        if libffi_lib not in current_dyld:
            os.environ["DYLD_LIBRARY_PATH"] = f"{libffi_lib}:{current_dyld}" if current_dyld else libffi_lib
    if os.path.exists(libffi_include):
        current_cppflags = os.environ.get("CPPFLAGS", "")
        os.environ["CPPFLAGS"] = f"-I{libffi_include} {current_cppflags}".strip()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )
