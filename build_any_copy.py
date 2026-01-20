import os
def compile_exe():
    choice = input("Build all? y/n:")
    if (choice == "y"):
        os.system("build_and_copy.bat all")
    else:
        os.system("build_and_copy.bat copy")

if __name__ == "__main__":
    compile_exe()