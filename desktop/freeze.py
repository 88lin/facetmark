"""PyInstaller entry point. Built and executed only on GitHub Actions."""
from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()
    from facetmark.desktop import main
    main()
