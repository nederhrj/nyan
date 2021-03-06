from setuptools import setup

setup(
    name='nyan',
    version='0.1.0',
    packages=['nyan', 'nyan.article_ranker', 'nyan.shared_modules', 'nyan.shared_modules.utils',
              'nyan.shared_modules.models', 'nyan.shared_modules.py21578', 'nyan.shared_modules.unit_tests',
              'nyan.shared_modules.feature_extractor', 'nyan.shared_modules.feature_extractor.esa',
              'nyan.feature_extractor', 'nyan.user_model_trainer', 'frontend'],
    url='https://github.com/nederhrj/nyan',
    license='LICENSE.txt',
    author='Rene Nederhand',
    author_email='rene@nederhand.net',
    description='NYAN is a news filtering engine written in Python and some Ruby.',
    long_description=open('README.txt').read(),
    install_requires=[
        "pyyaml >= 3.10",
        "gensim >= 0.8.6",
        "numpy >= 1.7.1",
        "scipy >= 0.12.0",
        "stomp.py >= 3.1.5",
        "scikit-learn >= 0.13.1",
        "flask >= 0.10.1",
        "flask-login >= 0.2.7",
        "mongoengine >= 0.8.4",
        "nltk >= 2.0.4",
    ],
)
