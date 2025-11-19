from segittur_commons.app.infrastructure.ai.llm.llm_provider import LlmProvider

llm: dict = {}


def load_llm_model(model_name, id=None, temperature=0.5, max_tokens=None, model_kwargs={}):
    model_id = id or model_name

    if model_id in llm:
        return llm[model_id]

    open_ai_model = LlmProvider.create_llm(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        model_kwargs=model_kwargs,
    )

    llm[model_id] = open_ai_model
    return open_ai_model
