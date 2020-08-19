import setuptools


with open('README.md', 'r') as fh:
    long_description = fh.read()


setuptools.setup(
    name='transferwise',
    version='0.0.1',
    author='Marcin Staniszczak',
    author_email='marcin@staniszczak.pl',
    description='A TransferWise library for Python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/useme-com/transferwise',
    packages=setuptools.find_packages(),
    license='BSD-3-Clause',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
    ],
    install_requires=open('requirements.txt', 'r').read().splitlines(),
    python_requires='>=3.6',
)
