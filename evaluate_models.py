"""
@author: Adityam Ghosh
Date: 10-30-2023

"""

from typing import Callable, List, Dict, Any, Tuple
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.data as td
import pytorch_lightning as pl
import torchvision
import os
import sys
import argparse
import yaml

from sklearn.metrics import accuracy_score
from trainer import LitMobileCLiP
from transformers import CLIPTokenizerFast
from utility.datasets import ZeroShotTextVisualDataset
from PIL import Image

from rich.progress import (
    Progress,
    MofNCompleteColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TextColumn,
    BarColumn,
)

import torch.multiprocessing

torch.multiprocessing.set_sharing_strategy("file_system")

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def text_process(txt: str, tokenizer: Callable, max_length: int) -> torch.Tensor:
    """
    Function to obtain the text captions as a torch Tensor
    """
    tok_outputs = tokenizer(
        txt,
        max_length=max_length,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )

    return tok_outputs


def get_text_tensors(text_captions: List, model: Callable) -> torch.Tensor:
    """Function to obtain the text tensors for all the captions"""

    prog_bar = Progress(
        TextColumn("[progress.percentage] {task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    )

    text_tensors = []

    with prog_bar as p:
        n_captions = len(text_captions)

        for i in p.track(range(n_captions), description="Getting text tensors"):
            txt = text_captions[i]["input_ids"].to("cuda:0")
            attn_mask = text_captions[i]["attention_mask"].float().to("cuda:0")
            text_tensors.append(
                F.normalize(model.encode_text(txt, attn_mask), p=2, dim=-1)
                .detach()
                .cpu()
            )

    concat_text_tensor = torch.cat(text_tensors, dim=0)
    return concat_text_tensor


def evaluate(dataloader: Any, model: Callable, text_tensors: torch.Tensor) -> float:
    """Function to evaluate the model"""

    prog_bar = Progress(
        TextColumn("[progress.percentage] {task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    )

    true_labels = list()
    pred_labels = list()

    with prog_bar as p:
        model.eval()
        for batch in p.track(dataloader, description="Evaluating Model"):
            img = batch["img"]
            label = batch["label"]

            img_encoding = model.encode_image(img.to("cuda:0"))
            similarities = (
                text_tensors.to("cuda:0") @ F.normalize(img_encoding, p=2, dim=-1).t()
            )
            pred_label = torch.argmax(similarities, dim=0)

            true_labels.append(label.detach().numpy())
            pred_labels.append(pred_label.detach().cpu().numpy())

    true_labels = np.asarray(true_labels)
    pred_labels = np.asarray(pred_labels)

    unique_preds, counts = np.unique(pred_labels, return_counts=True)
    unique_preds = unique_preds.reshape(-1, 1)
    counts = counts.reshape(-1, 1)
    print(f"frequency of each predicted classes by the model")
    print(np.hstack((unique_preds, counts)))

    return accuracy_score(true_labels, pred_labels)


if __name__ == "__main__":
    torch.cuda.empty_cache()

    parser = argparse.ArgumentParser(
        prog="evaluation script",
        description="Evaluation script for the Mobile CLiP model",
    )

    parser.add_argument(
        "--csv_path",
        "-C",
        required=True,
        type=str,
        help="the csv file path for the data",
    )

    parser.add_argument(
        "--model_checkpoint",
        "-c",
        required=True,
        type=str,
        help="the model checkpoint location",
    )

    parser.add_argument(
        "--config_path",
        "-p",
        required=True,
        type=str,
        help="the config path for the models",
    )

    args = parser.parse_args()

    csv_path = args.csv_path
    model_checkpoint = args.model_checkpoint
    config_path = args.config_path

    cfg = None
    with open(config_path, "r") as fp:
        try:
            cfg = yaml.safe_load(fp)
        except yaml.YAMLError as exc:
            print(exc)

    df = pd.read_csv(csv_path)
    # print(df.loc[df["label"].isna()])
    # print(torch.load(model_checkpoint)["state_dict"].keys())
    model = LitMobileCLiP.load_from_checkpoint(model_checkpoint, config=cfg)
    model.freeze()
    # clip_model = model.clip_model

    text_tokenizer = CLIPTokenizerFast.from_pretrained("openai/clip-vit-base-patch32")

    integer_label_map = {k: idx for idx, k in enumerate(df["text"].unique())}
    print(integer_label_map)

    unique_captions = df["text"].unique().tolist()

    df["label"] = df["text"].map(integer_label_map)

    tokenized_txts = [
        text_process(txt, text_tokenizer, cfg["text_model"]["max_seq_length"])
        for txt in unique_captions
    ]

    txt_tensors = get_text_tensors(text_captions=tokenized_txts, model=model)

    transformations = torchvision.transforms.Compose(
        [
            torchvision.transforms.Resize((224, 224)),
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize(
                (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)
            ),
        ]
    )

    # img_tensors = get_img_tensors(df["image_path"].tolist(), transformations)

    test_ds = ZeroShotTextVisualDataset(
        data=df,
        transformations=transformations,
        config=cfg,
    )

    test_dl = td.DataLoader(test_ds, batch_size=1, shuffle=False, num_workers=1)

    acc = evaluate(test_dl, model, txt_tensors)

    print(f"Zero-shot accuracy: {acc*100:.2f}%")
