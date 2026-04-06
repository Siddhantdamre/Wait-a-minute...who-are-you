import subprocess
with open('full_output.txt', 'w') as f:
    result = subprocess.run(['python', '-m', 'pytest', '-q', 'tests/test_golden_c6.py', 'tests/test_transfer_regression.py'], capture_output=True, text=True)
    f.write(result.stdout)
    f.write('\nErrors:\n')
    f.write(result.stderr)
