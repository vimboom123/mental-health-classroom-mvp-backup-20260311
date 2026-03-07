while True:
    try:
        a = float(input("First number: "))
        op = input("Operator (+, -, *, /): ").strip()
        if op not in ("+", "-", "*", "/"):
            print(f"Invalid operator: {op}")
            continue
        b = float(input("Second number: "))
    except ValueError:
        print("Invalid number. Please enter a numeric value.")
        continue

    if op == "/" and b == 0:
        print("Error: Division by zero.")
    elif op == "+":
        print(f"= {a + b}")
    elif op == "-":
        print(f"= {a - b}")
    elif op == "*":
        print(f"= {a * b}")
    elif op == "/":
        print(f"= {a / b}")

    if input("Calculate again? (y/n): ").strip().lower() != "y":
        break
