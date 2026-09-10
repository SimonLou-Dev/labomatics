from . import alpine, debian, el, ubuntu

images_list = [
    alpine.alpine_3_24_server,
    debian.trixie_server,
    el.fedora_44_server,
    ubuntu.resolute_server
]

__all__ = ["images_list"]