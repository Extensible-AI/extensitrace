from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='extensilog',
    version='0.1.0',
    packages=find_packages(include=['extensilog', 'extensilog.*']),
    install_requires=required,
    author='Parth Sareen, Omkaar Kamath',
    author_email='parth@extensible.dev, omkaar@extensible.dev',
    description='A logger for tracking your agent workflow',
    url='https://github.com/Extensible-AI/extensilog/',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
