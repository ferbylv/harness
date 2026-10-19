from harness.clipboard import sniff_mime
from harness.content import has_images, text_of
from harness.draft import Draft


PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_sniff_png():
    assert sniff_mime(PNG) == "image/png"


def test_expand_merges_image_and_text():
    draft = Draft()
    chip = draft.add_image(PNG, "image/png")
    assert chip == "[Image #1]"
    buffer = f"{chip} look at this"
    content = draft.expand(buffer)
    assert isinstance(content, list)
    assert content[0]["type"] == "image_url"
    assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert content[1] == {"type": "text", "text": " look at this"}
    assert "[image]" in text_of(content)
    assert has_images(content)


def test_large_paste_placeholder_expands():
    draft = Draft()
    blob = "x" * 1500
    chip = draft.add_paste(blob)
    assert "1500 chars" in chip
    assert blob not in chip
    assert draft.expand(chip + "!") == blob + "!"


def test_text_only_stays_string():
    assert Draft().expand("hello") == "hello"
