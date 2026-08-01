def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def calculate(operation, x, y):
    print(f"Calculating {operation} of {x} and {y}")
    if operation == "add":
        result = add(x, y)
    elif operation == "multiply":
        result = multiply(x, y)
    else:
        result = None
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    calculate("add", 5, 3)
    calculate("multiply", 4, 7)
