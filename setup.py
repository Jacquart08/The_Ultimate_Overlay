from setuptools import setup, find_packages

setup(
    name="The_Ultimate_Overlay_App",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6",
        "keyboard",
        "torch>=2.0.0",
        "transformers>=4.30.0",
        "accelerate>=0.20.0",
        "bitsandbytes>=0.39.0",
        "sentencepiece>=0.1.99",
        "protobuf>=3.20.0",
    ],
    python_requires=">=3.8",
) 