from src.converters.image_converter import convert_image
from unittest.mock import patch, MagicMock

@patch('src.converters.image_converter.ImageEnhance')
@patch('pytesseract.image_to_string')
@patch('src.converters.image_converter.Image.open')
def test_debug(mock_open, mock_ocr, mock_enhance):
    mock_img = MagicMock()
    mock_open.return_value = mock_img
    mock_ocr.return_value = "Extracted OCR text"
    res = convert_image("dummy.png")
    print(res)

test_debug()
