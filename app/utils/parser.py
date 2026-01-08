def parse_agent_output(content) -> str:
    """
    Normalize LangChain agent output into plain text for Telegram.
    Mengabaikan blok 'thought' dan memastikan newline (\\n) dirender dengan benar.
    """
    if not content:
        return ""
        
    res = ""
    if isinstance(content, str):
        res = content
    elif isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                val = item.get("text") or item.get("content")
                if val and isinstance(val, str):
                    texts.append(val)
        res = "\n".join(texts)
    else:
        res = str(content)

    if res:
        res = res.replace("\\n", "\n")
        res = res.strip()
    return res
