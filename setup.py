from setuptools import setup, find_packages

setup(
    name='rate_limiter',
    version='0.1.0',
    description='A rate limiter library for managing API key usage.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/sifeiwl/rate_limiter.git',  # 项目的URL
    packages=find_packages(),
    install_requires=[
        'redis',  # 依赖的库
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
