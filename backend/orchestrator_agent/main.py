from langchain_core.language_models import BaseLLM
import inspect

def main():
    print("Hello from orchestrator-agent!")
    print(f"Using LLM model: {llm.model_name}")

    # Find all LLM instances in the current modules
    for name, obj in inspect.getmembers(globals()):
        if isinstance(obj, BaseLLM):
            print(f"Found LLM: {name}, Model: {obj.model_name}")


if __name__ == "__main__":
    main()
