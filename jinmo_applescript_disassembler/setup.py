from setuptools import setup, find_packages

setup(
    name="jinmo_applescript_disassembler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    author="Jinmo",
    description="A simple run-only applescript disassembler",
    url="https://github.com/Jinmo/applescript-disassembler",
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "applescript_disassemble = jinmo_applescript_disassembler.disassembler:cli",
        ],
    },
)