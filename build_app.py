import PyInstaller.__main__
import platform
import os
import shutil

def build():
    print("Starting build process...")
    
    # clear dist and build folders if they exist
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')

    system = platform.system()
    
    # Common options
    options = [
        'run_gui.py',                  # Script to build
        '--name=HeadphoneTestApp',     # Name of the executable
        '--onefile',                   # Create a single executable file
        '--windowed',                  # No console window (GUI only)
        '--clean',                     # Clean cache
        '--paths=.',                   # Add current directory to path
        # '--add-data=src;src',        # (Optional) Explicitly add src if analysis fails (Windows format)
    ]
    
    # OS specific adjustments
    if system == 'Windows':
        print("Detected Windows system.")
        # On Windows, add-data separator is ;
        # options.append('--add-data=src;src') 
        pass
    elif system == 'Darwin': # macOS
        print("Detected macOS system.")
        # On Mac, add-data separator is :
        # options.append('--add-data=src:src')
        options.append('--target-architecture=universal2') # Support M1/Intel
    elif system == 'Linux':
        print("Detected Linux system.")
        
    print(f"Running PyInstaller with options: {options}")
    
    # Run PyInstaller
    try:
        PyInstaller.__main__.run(options)
        print("\nBuild completed successfully!")
        print(f"Executable is located in the 'dist' folder.")
        # Debugging step: print what's in dist
        if os.path.exists('dist'):
            print("Contents of dist folder:")
            for item in os.listdir('dist'):
                print(f" - {item}")
        else:
            print("ERROR: dist folder was not created!")
    except Exception as e:
        print(f"\nBuild failed: {e}")

if __name__ == "__main__":
    build()
