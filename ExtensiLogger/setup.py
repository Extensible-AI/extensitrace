from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='extensilogger',
    version='0.1',
    packages=find_packages(),
    install_requires=required,
    # additional metadata about your package
    author='Parth Sareen, Omkaar Kamath',
    author_email='parth@extensible.dev, omkaar@extensible.dev',
    description='A logger for tracking your agent workflow',
    url='https://github.com/yourusername/yourprojectname',  # Optional
)