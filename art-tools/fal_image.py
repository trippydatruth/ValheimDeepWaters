# Generates reference / concept images with fal.ai FLUX [dev] - text to image, or image to image from a local picture.
# Runs on Blender's own Python, with the client installed in art-tools/_vendor (git-ignored):
#   "C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe" -m pip install --target art-tools\_vendor fal-client
# The key is read from FAL_KEY in the environment or the repo's .env (git-ignored); it is never printed.
#
#   python fal_image.py --prompt "..." --out <new folder> [--image ref.png --strength 0.85] [--size square_hd] [--seed 7]
#                       [--num 1] [--format png]
# Each image costs money (FLUX dev: $0.025 per megapixel, image to image $0.03; square_hd is ~1 MP): it says the estimate
# before sending. The output folder must not exist yet, so nothing is overwritten.
import argparse, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_vendor"))

SIZES = {"square_hd": (1024, 1024), "square": (512, 512), "portrait_4_3": (768, 1024), "portrait_16_9": (576, 1024),
         "landscape_4_3": (1024, 768), "landscape_16_9": (1024, 576)}


def load_key():
    """FAL_KEY from the environment, else from the repo's .env. The value stays out of every message."""
    if os.environ.get("FAL_KEY"): return
    env = os.path.join(HERE, "..", ".env")
    if os.path.exists(env):
        for line in open(env, encoding="utf-8"):
            k, _, v = line.strip().partition("=")
            if k.strip() == "FAL_KEY" and v.strip():
                os.environ["FAL_KEY"] = v.strip().strip('"').strip("'")
                return
    raise SystemExit("No FAL_KEY: put a line FAL_KEY=... in the .env at the repo root (https://fal.ai/dashboard/keys).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True, help="a new folder for the images")
    ap.add_argument("--image", help="a local picture to start from (image to image)")
    ap.add_argument("--strength", type=float, default=0.95, help="image to image: how far from the picture (0.01-1)")
    ap.add_argument("--size", default="square_hd", choices=sorted(SIZES), help="text to image only")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--num", type=int, default=1, choices=range(1, 5))
    ap.add_argument("--steps", type=int)
    ap.add_argument("--format", default="png", choices=("png", "jpeg"))
    a = ap.parse_args()

    if os.path.exists(a.out): raise SystemExit("exists, kept: " + a.out)
    load_key()
    import fal_client

    args = {"prompt": a.prompt, "num_images": a.num, "output_format": a.format}
    if a.seed is not None: args["seed"] = a.seed
    if a.steps: args["num_inference_steps"] = a.steps
    if a.image:
        endpoint, rate = "fal-ai/flux/dev/image-to-image", 0.03
        args["image_url"] = fal_client.upload_file(a.image)
        args["strength"] = a.strength
        mp = 1.0                                   # (the output follows the input picture's size; about 1 MP for a 1024 picture)
    else:
        endpoint, rate = "fal-ai/flux/dev", 0.025
        args["image_size"] = a.size
        w, h = SIZES[a.size]; mp = w * h / 1e6
    print(f"FAL {endpoint}: {a.num} image(s), about ${rate * mp * a.num:.3f}")

    handle = fal_client.submit(endpoint, arguments=args)
    print("FAL request", handle.request_id)        # kept, so a stalled job can be looked up instead of paid for twice
    result = handle.get()

    os.makedirs(a.out)
    for i, im in enumerate(result["images"]):
        p = os.path.join(a.out, f"fal_{result['seed']}_{i}.{a.format}")
        urllib.request.urlretrieve(im["url"], p)
        print("SAVED", p)
    with open(os.path.join(a.out, "prompt.txt"), "w", encoding="utf-8") as f:
        f.write(f"{endpoint}\nseed {result['seed']}\n{a.prompt}\n" + (f"from {a.image} strength {a.strength}\n" if a.image else ""))


if __name__ == "__main__":
    main()
