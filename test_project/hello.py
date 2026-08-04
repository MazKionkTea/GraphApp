def greet(name):
    print(f"Hello, {name}!")
    return f"Greeting: {name}"

def main():
    result = greet("World")
    print(result)
    return result

if __name__ == "__main__":
    main()
