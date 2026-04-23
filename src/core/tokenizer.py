def count_tokens(text: str, tokenizer: str = "approx") -> int:
    if tokenizer == "approx":
        return max(1, len(text) // 4)
    try:
        import tiktoken

        return len(tiktoken.get_encoding(tokenizer).encode(text))
    except ImportError:
        raise RuntimeError("Install tiktoken: pip install caveman[tiktoken]")
