def get_list_args_from_str(list_arg: str) -> list[str]:
    return [arg.strip() for arg in list_arg.split(",")]
