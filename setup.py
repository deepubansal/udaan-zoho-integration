import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="udaan-zoho-integration",
    version="0.0.1",
    author="deepubansal",
    author_email="deepu.bansal@gmail.com",
    description="Udaan Zoho Integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/deepubansal/udaan-zoho-integration",
    packages=setuptools.find_packages(),
    classifiers=[
    ]
)