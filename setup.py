import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="license_scanner",
    version="0.0.0",
    author="Steve Klassen",
    author_email="steve.klassen@sensonic.com",
    description="Utility for scanning projects for third-party licenses",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://scm01.frauscher.intern/fts/rnd/docker/license-check.git",
    packages=setuptools.find_packages(),
    install_requires=[
        'fpdf', 'requests'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',
)
