import sys
from converters.ig_converter import convert_ig_link

if __name__ == "__main__":
    url = "https://www.instagram.com/p/DZucoBjiQxd/"
    print("Testing IG Converter with:", url)
    res = convert_ig_link(url)
    print("Result Length:", len(res))
    print(res[:500])
