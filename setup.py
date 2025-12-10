from setuptools import setup, find_packages

setup(
    name="applescript_decompiler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "jinmo_applescript_disassembler @ file:jinmo_applescript_disassembler"
    ],
    author="pberba",
    description="A decompiler for run-only applescripts",
    url="https://github.com/pberba/applescript-decompiler",
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "applescript_decompile = applescript_decompiler.decompiler:cli",
        ],
    },
    package_data={
        "applescript_decompiler": ["data/*.sdef"],  # adjust to your structure
    },
)