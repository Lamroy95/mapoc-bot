import cv2


def make_preview(filename, max_dim=1080):
    output_name = f"prev_{filename}"
    img = cv2.imread(filename, cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    scale = max_dim / max(h, w)
    img = cv2.resize(img, (int(w * scale), int(h * scale)), cv2.INTER_AREA)
    # img /= 255.0
    cv2.imwrite(
        output_name,
        img,
        # [cv2.IMWRITE_PNG_COMPRESSION, 5]
    )

    return output_name
