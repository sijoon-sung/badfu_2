"""Download an unchanged CIFAR archive mirror, verify torchvision's official MD5."""
from pathlib import Path
from torchvision.datasets.utils import check_integrity, download_url, extract_archive

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "upstream/data_prepare/data/cifar10"
URL = "https://huggingface.co/datasets/MIT-OL-AI-D/cifar-10-python/resolve/a480072/cifar-10-python.tar.gz"
MD5 = "c58f30108f718f92721af3b95e74349a"

if __name__ == "__main__":
    download_url(URL, str(ROOT / "data"), "cifar-10-python.tar.gz", md5=MD5)
    archive = ROOT / "data/cifar-10-python.tar.gz"
    assert check_integrity(str(archive), MD5)
    extract_archive(str(archive), str(DEST))
    print("CIFAR-10 extracted; original torchvision MD5 verified", flush=True)
