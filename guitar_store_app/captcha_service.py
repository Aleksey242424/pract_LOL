# captcha_service.py
from go_captcha_py import slide, store

captcha_store = store.MemoryStore(ttl=600)


def generate_captcha() -> dict:
    data = slide.make_default_captcha().generate()
    block = data.get_data()  # объект Block: .x, .y, .width, .height

    captcha_id = store.gen_key()
    captcha_store.set(captcha_id, {
        "x": block.x,
        "y": block.y,
    })

    return {
        "captcha_id": captcha_id,
        "image_base64": data.get_master_image().to_base64(),
        "thumb_base64": data.get_tile_image().to_base64(),
        "tile_y": block.y,
        "tile_width": block.width,
        "tile_height": block.height,
    }


def verify_captcha(captcha_id: str, user_x: int) -> bool:
    block = captcha_store.pop(captcha_id)
    if block is None:
        return False

    return slide.validate(
        user_x, block["y"],
        block["x"], block["y"],
        padding=10,
    )