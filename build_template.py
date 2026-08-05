"""
Generate a clean X-download pattern template shortcut (unsigned).
API endpoints are placeholders for the user to fill in.
"""
from __future__ import annotations

import json
import plistlib
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "template"
OUT.mkdir(exist_ok=True)


def uid() -> str:
    return str(uuid.uuid4()).upper()


def attachment(value: dict) -> dict:
    return {"Value": value, "WFSerializationType": "WFTextTokenAttachment"}


def text_with_vars(parts: list) -> dict:
    """Build WFTextTokenString from alternating str and attachment dicts.
    parts items: str OR ("var", name) OR ("out", uuid, name) OR ("ext",)
    """
    s = ""
    attachments: dict = {}
    for p in parts:
        if isinstance(p, str):
            s += p
        elif p[0] == "var":
            pos = len(s)
            s += "\ufffc"
            attachments[f"{{{pos}, 1}}"] = {"VariableName": p[1], "Type": "Variable"}
        elif p[0] == "out":
            pos = len(s)
            s += "\ufffc"
            attachments[f"{{{pos}, 1}}"] = {
                "OutputUUID": p[1],
                "Type": "ActionOutput",
                "OutputName": p[2],
            }
        elif p[0] == "ext":
            pos = len(s)
            s += "\ufffc"
            attachments[f"{{{pos}, 1}}"] = {"Type": "ExtensionInput"}
    return {
        "Value": {"string": s, "attachmentsByRange": attachments},
        "WFSerializationType": "WFTextTokenString",
    }


def header_dict(items: dict[str, str]) -> dict:
    field_items = []
    for k, v in items.items():
        field_items.append(
            {
                "WFKey": {
                    "Value": {"string": k},
                    "WFSerializationType": "WFTextTokenString",
                },
                "WFItemType": 0,
                "WFValue": {
                    "Value": {"string": v},
                    "WFSerializationType": "WFTextTokenString",
                },
            }
        )
    return {
        "Value": {"WFDictionaryFieldValueItems": field_items},
        "WFSerializationType": "WFDictionaryFieldValue",
    }


def json_body_with_url(key: str = "url") -> dict:
    return {
        "Value": {
            "WFDictionaryFieldValueItems": [
                {
                    "WFKey": {
                        "Value": {"string": key},
                        "WFSerializationType": "WFTextTokenString",
                    },
                    "WFItemType": 0,
                    "WFValue": text_with_vars([("var", "inputURL")]),
                }
            ]
        },
        "WFSerializationType": "WFDictionaryFieldValue",
    }


def set_var_from_extension(name: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
        "WFWorkflowActionParameters": {
            "WFInput": attachment({"Type": "ExtensionInput"}),
            "WFVariableName": name,
        },
    }


def comment(text: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.comment",
        "WFWorkflowActionParameters": {"WFCommentActionText": text},
    }


def menu_start(prompt: str, items: list[str], group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.choosefrommenu",
        "WFWorkflowActionParameters": {
            "WFMenuPrompt": prompt,
            "WFControlFlowMode": 0,
            "WFMenuItems": items,
            "GroupingIdentifier": group,
        },
    }


def menu_case(title: str, group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.choosefrommenu",
        "WFWorkflowActionParameters": {
            "WFMenuItemTitle": title,
            "GroupingIdentifier": group,
            "WFControlFlowMode": 1,
        },
    }


def menu_end(group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.choosefrommenu",
        "WFWorkflowActionParameters": {
            "GroupingIdentifier": group,
            "WFControlFlowMode": 2,
        },
    }


def if_has_value(output_uuid: str, output_name: str, group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
        "WFWorkflowActionParameters": {
            "WFInput": {
                "Type": "Variable",
                "Variable": attachment(
                    {
                        "Type": "ActionOutput",
                        "OutputName": output_name,
                        "OutputUUID": output_uuid,
                        "Aggrandizements": [
                            {
                                "Type": "WFCoercionVariableAggrandizement",
                                "CoercionItemClass": "WFStringContentItem",
                            }
                        ],
                    }
                ),
            },
            "WFControlFlowMode": 0,
            "GroupingIdentifier": group,
            "WFCondition": 100,  # Has Any Value
        },
    }


def if_else(group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
        "WFWorkflowActionParameters": {
            "WFControlFlowMode": 1,
            "GroupingIdentifier": group,
        },
    }


def if_end(group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
        "WFWorkflowActionParameters": {
            "WFControlFlowMode": 2,
            "GroupingIdentifier": group,
        },
    }


def notify(body: str, uuid_str: str | None = None) -> dict:
    params = {"WFNotificationActionBody": body}
    if uuid_str:
        params["UUID"] = uuid_str
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.notification",
        "WFWorkflowActionParameters": params,
    }


def save_to_album(from_uuid: str, from_name: str, uuid_str: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.savetocameraroll",
        "WFWorkflowActionParameters": {
            "WFInput": attachment(
                {
                    "OutputUUID": from_uuid,
                    "Type": "ActionOutput",
                    "OutputName": from_name,
                }
            ),
            "UUID": uuid_str,
        },
    }


def get_dict_value(from_uuid: str, from_name: str, key: str, uuid_str: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
        "WFWorkflowActionParameters": {
            "WFInput": attachment(
                {
                    "OutputUUID": from_uuid,
                    "Type": "ActionOutput",
                    "OutputName": from_name,
                }
            ),
            "UUID": uuid_str,
            "WFDictionaryKey": key,
        },
    }


def download_media(url_uuid: str, url_name: str, uuid_str: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": {
            "ShowHeaders": False,
            "UUID": uuid_str,
            "WFURL": text_with_vars([("out", url_uuid, url_name)]),
        },
    }


def api_post_json(url: str, uuid_str: str, body_key: str = "url") -> dict:
    """Placeholder: POST JSON {url: inputURL} to your parser."""
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": {
            "ShowHeaders": True,
            "UUID": uuid_str,
            "WFURL": url,
            "WFHTTPMethod": "POST",
            "WFHTTPBodyType": "JSON",
            "WFJSONValues": json_body_with_url(body_key),
            "WFHTTPHeaders": header_dict(
                {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
            ),
        },
    }


def api_get_query(base_with_placeholder_note: str, uuid_str: str) -> dict:
    """GET yourAPI?url=<inputURL> — base string ends before query value."""
    # URL = base + inputURL variable
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": {
            "ShowHeaders": False,
            "UUID": uuid_str,
            "WFURL": text_with_vars([base_with_placeholder_note, ("var", "inputURL")]),
        },
    }


def match_mp4(from_uuid: str, from_name: str, uuid_str: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.text.match",
        "WFWorkflowActionParameters": {
            "WFMatchTextPattern": r'https?:[^\s"\\]+\.mp4(?:\?[^\s"]*)?',
            "text": text_with_vars([("out", from_uuid, from_name)]),
            "UUID": uuid_str,
        },
    }


def repeat_each_start(from_uuid: str, from_name: str, group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.repeat.each",
        "WFWorkflowActionParameters": {
            "WFInput": attachment(
                {
                    "OutputUUID": from_uuid,
                    "Type": "ActionOutput",
                    "OutputName": from_name,
                }
            ),
            "GroupingIdentifier": group,
            "WFControlFlowMode": 0,
            "UUID": uid(),
        },
    }


def repeat_each_end(group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.repeat.each",
        "WFWorkflowActionParameters": {
            "GroupingIdentifier": group,
            "WFControlFlowMode": 2,
        },
    }


# --- Build workflow ---

MENU = uid()
IF_SINGLE = uid()
IF_MULTI = uid()
IF_IMG = uid()
IF_GIF = uid()
REP_MULTI = uid()
REP_IMG = uid()

# Placeholder APIs — replace with your own
API_SINGLE = "https://YOUR_API.example/v1/single"
API_MULTI = "https://YOUR_API.example/v1/multi"
API_IMAGE = "https://YOUR_API.example/v1/image"
API_GIF = "https://YOUR_API.example/v1/gif"

# Expected JSON shapes (document for user):
# single: { "url": "https://...mp4" }
# multi:  { "urls": ["https://...mp4", ...] }
# image:  { "urls": ["https://...jpg", ...] }
# gif:    { "url": "https://...gif" }  or frames handled by your API as mp4/gif file

u_api_s = uid()
u_key_s = uid()
u_dl_s = uid()
u_save_s = uid()

u_api_m = uid()
u_key_m = uid()
u_dl_m = uid()
u_save_m = uid()

u_api_i = uid()
u_key_i = uid()
u_dl_i = uid()
u_save_i = uid()

u_api_g = uid()
u_key_g = uid()
u_dl_g = uid()
u_save_g = uid()

actions = [
    comment(
        "模板：X/链接作品下载骨架\n"
        "1) 分享表或剪贴板传入链接 → inputURL\n"
        "2) 选类型 → 请求你的解析 API\n"
        "3) 取媒体地址 → 下载 → 存相册\n\n"
        "请把下面 4 个 API 地址改成你自己的。\n"
        "约定返回 JSON：\n"
        "  单视频/GIF: {\"url\": \"...\"}\n"
        "  多视频/图片: {\"urls\": [\"...\", \"...\"]}"
    ),
    set_var_from_extension("inputURL"),
    menu_start("选择作品类型", ["单视频", "多视频", "图片", "GIF"], MENU),
    # ----- 单视频 -----
    menu_case("单视频", MENU),
    api_post_json(API_SINGLE, u_api_s, "url"),
    get_dict_value(u_api_s, "URL的内容", "url", u_key_s),
    if_has_value(u_key_s, "词典值", IF_SINGLE),
    download_media(u_key_s, "词典值", u_dl_s),
    save_to_album(u_dl_s, "URL的内容", u_save_s),
    notify("✅ 单视频已保存"),
    if_else(IF_SINGLE),
    notify("❌ 单视频解析失败"),
    if_end(IF_SINGLE),
    # ----- 多视频 -----
    menu_case("多视频", MENU),
    api_post_json(API_MULTI, u_api_m, "url"),
    get_dict_value(u_api_m, "URL的内容", "urls", u_key_m),
    if_has_value(u_key_m, "词典值", IF_MULTI),
    repeat_each_start(u_key_m, "词典值", REP_MULTI),
    # Repeat Item as URL download — use Repeat Item magic variable via Extension-like:
    {
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": {
            "ShowHeaders": False,
            "UUID": u_dl_m,
            "WFURL": {
                "Value": {
                    "string": "\ufffc",
                    "attachmentsByRange": {
                        "{0, 1}": {
                            "Type": "Variable",
                            "VariableName": "Repeat Item",
                        }
                    },
                },
                "WFSerializationType": "WFTextTokenString",
            },
        },
    },
    save_to_album(u_dl_m, "URL的内容", u_save_m),
    repeat_each_end(REP_MULTI),
    notify("✅ 多视频已保存"),
    if_else(IF_MULTI),
    notify("❌ 多视频解析失败"),
    if_end(IF_MULTI),
    # ----- 图片 -----
    menu_case("图片", MENU),
    api_post_json(API_IMAGE, u_api_i, "url"),
    get_dict_value(u_api_i, "URL的内容", "urls", u_key_i),
    if_has_value(u_key_i, "词典值", IF_IMG),
    repeat_each_start(u_key_i, "词典值", REP_IMG),
    {
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": {
            "ShowHeaders": False,
            "UUID": u_dl_i,
            "WFURL": {
                "Value": {
                    "string": "\ufffc",
                    "attachmentsByRange": {
                        "{0, 1}": {
                            "Type": "Variable",
                            "VariableName": "Repeat Item",
                        }
                    },
                },
                "WFSerializationType": "WFTextTokenString",
            },
        },
    },
    save_to_album(u_dl_i, "URL的内容", u_save_i),
    repeat_each_end(REP_IMG),
    notify("✅ 图片已保存"),
    if_else(IF_IMG),
    notify("❌ 图片解析失败"),
    if_end(IF_IMG),
    # ----- GIF -----
    menu_case("GIF", MENU),
    api_post_json(API_GIF, u_api_g, "url"),
    get_dict_value(u_api_g, "URL的内容", "url", u_key_g),
    if_has_value(u_key_g, "词典值", IF_GIF),
    download_media(u_key_g, "词典值", u_dl_g),
    save_to_album(u_dl_g, "URL的内容", u_save_g),
    notify("✅ GIF 已保存"),
    if_else(IF_GIF),
    notify("❌ GIF 解析失败"),
    if_end(IF_GIF),
    menu_end(MENU),
]

workflow = {
    "WFWorkflowClientVersion": "4711",
    "WFWorkflowMinimumClientVersion": 900,
    "WFWorkflowMinimumClientVersionString": "900",
    "WFWorkflowIcon": {
        "WFWorkflowIconStartColor": 431817727,
        "WFWorkflowIconGlyphNumber": 59750,
    },
    "WFWorkflowTypes": ["ActionExtension", "WFWorkflowTypeShowInSearch"],
    "WFQuickActionSurfaces": [],
    "WFWorkflowHasShortcutInputVariables": True,
    "WFWorkflowHasOutputFallback": False,
    "WFWorkflowOutputContentItemClasses": [],
    "WFWorkflowInputContentItemClasses": [
        "WFURLContentItem",
        "WFSafariWebPageContentItem",
        "WFStringContentItem",
        "WFRichTextContentItem",
    ],
    "WFWorkflowNoInputBehavior": {
        "Name": "WFWorkflowNoInputBehaviorGetClipboard",
        "Parameters": {},
    },
    "WFWorkflowImportQuestions": [],
    "WFWorkflowActions": actions,
}

(OUT / "workflow.json").write_text(
    json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8"
)
with (OUT / "template.shortcut").open("wb") as f:
    plistlib.dump(workflow, f, fmt=plistlib.FMT_BINARY)
with (OUT / "workflow.plist").open("wb") as f:
    plistlib.dump(workflow, f, fmt=plistlib.FMT_XML)

print("actions:", len(actions))
print("wrote:", OUT / "workflow.json")
print("wrote:", OUT / "template.shortcut")
print("wrote:", OUT / "workflow.plist")
