from setuptools import setup, find_packages

setup(
    name='personal-graph',
    version='0.1.8',
    description='Graph database in LibSQL',
    author='Anubhuti Bhardwaj',
    author_email='anubhutibhardwaj11@gmail.com',
    license='MIT',
    package_data={"personal_graph": ["py.typed"]},
    packages=["personal_graph"],
    install_requires=[
        'graphviz>=0.20.1',
        'jinja2>=3.1.3',
        'python-dotenv>=1.0.1',
        'sqlite-vss>=0.1.2',
        'openai>=1.14.2',
        'libsql-experimental>=0.0.28',
        'fastapi>=0.110.0',
        'uvicorn>=0.29.0',
        'sqlean-py>=3.45.1',
        'streamlit>=1.33.0',
        'types-pygments>=2.17.0.20240310',
        'types-decorator>=5.1.8.20240310',
        'networkx[default]>=3.3',
        'litellm>=1.35.26',
        'dspy-ai>=2.3.0',
        'instructor>=1.2.2',
        'vlite>=0.2.7',
    ],
    extras_require={
        'dev': [
            'pytest>=8.1.1',
            'ruff>=0.3.2',
            'mypy>=1.9.0',
        ],
        'scrollable-textbox': ['streamlit-scrollable-textbox'],
    },
    python_requires='>=3.11',
)