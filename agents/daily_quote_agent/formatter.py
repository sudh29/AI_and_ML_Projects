class Formatter:
    @staticmethod
    def to_platform_text(quote: str, caption: str, hashtags: str, platform: str) -> str:
        if platform == "twitter":
            text = f'"{quote}" — {caption} {hashtags}'
            return text[:280]
        else:
            return f'"{quote}"\n\n{caption}\n\n{hashtags}'
