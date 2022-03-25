import os
import arrow
import requests
import base64

dev_ids = [40322523]

def create_text(user_id, first_name, last_name, query, params) -> str:
    if params["volatile_level"]==0:
        dttm = ""
    elif params["volatile_level"]==1:
        dttm = arrow.now().format("YYYYMMDD")
    elif params["volatile_level"]==2:
        dttm = arrow.now().format("YYYYMMDDHHMMSS")
    value = int(
        hash(
            str(user_id)+dttm+query+str(params["id"])
        )
    )%100
    slope = (params["scale_high"] - params["scale_low"]) / 99
    value_new = int(params["scale_low"] + slope * value)
    txt_params = {
        "value": value_new,
        "unit": params.get("unit", ""),
        "first_name": first_name,
        "last_name": last_name
    }
    txt = params["template"]
    if params.get("limit_high"):
        txt_params["limit_low"] = params["limit_low"]
        txt_params["limit_up"] = params["limit_high"]
        if value_new<params["limit_low"]:
            txt = params["template_low"]
        elif value_new>=params["limit_high"]:
            txt = params["template_high"]
    txt = txt.format(**txt_params)
    if query:
        txt = "{0}, {1}{2}".format(query, txt[0].lower(), "".join(txt[1:]))
    else:
        txt = txt[0].upper() + "".join(txt[1:])
    return txt


class ImagebanApi:
    def __init__(self):
        client_id = os.environ.get("IMAGEBAN_CLIENT_ID")
        secret_key = os.environ.get("IMAGEBAN_SECRET_KEY")
        self.secret_key = secret_key
        self.base_url = "https://api.imageban.ru/v1"
        s = requests.Session()
        s.headers.update({"Authorization": "TOKEN "+self.client_id})
        self.api = s
    
    def image_upload(self, image, use_auth=False):
        data={"image": image}
        if use_auth:
            data["secret_key"] = self.secret_key
        return self.api.post(self.base_url, data=data)


def upload_photo(msg):
    url = msg.text
    if msg.photo:
        img = base64.b64encode(msg.photo[-1].get_file().download_as_bytearray())
        img_info = ImagebanApi().image_upload(img).json()
        url = img_info["data"]["link"]
    return url

