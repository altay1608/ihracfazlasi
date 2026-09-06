def password_is_strong(password):
    value = str(password or "")
    return all(
        (
            len(value) >= 10,
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
        )
    )
