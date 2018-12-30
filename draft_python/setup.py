import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mtg_draft_ai",
    version="0.0.1",
    description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/uponthesun/mtg-draft-ai",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=['toml'],
    extras_require={
        'test': ['pytest', 'mock', 'pytest-cov']
    }
)
