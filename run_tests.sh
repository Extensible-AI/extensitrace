python3 -m venv venv
source venv/bin/activate
pip install .
python tests/simple_test.py
python tests/stress_test.py
python tests/batch_testing.py
python tests/verify_extra.py