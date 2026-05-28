from streamlit.testing.v1 import AppTest
import sys

def main():
    try:
        at = AppTest.from_file("app.py")
        at.run()
        print("Success running AppTest!")
        print("Inputs found:", [input.label for input in at.text_input])
        print("Buttons found:", [btn.label for btn in at.button])
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
