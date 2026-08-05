"""
Build unsigned iOS Shortcut: mode menu + nichind public API.
Output: dist/X下载-自用.shortcut
"""
from __future__ import annotations

import json
import plistlib
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dist"
OUT.mkdir(exist_ok=True)

NICHIND = "https://dwnld.nichind.dev/"

# Chinese Shortcuts magic variable names (国行 iOS)
REPEAT_ITEM = "重复项目"
URL_CONTENT = "URL的内容"
DICT_VALUE = "词典值"
LIST_NAME = "列表"
LIST_ITEM = "列表中的项目"


def uid() -> str:
    return str(uuid.uuid4()).upper()


def att(value: dict) -> dict:
    return {"Value": value, "WFSerializationType": "WFTextTokenAttachment"}


def text_parts(parts: list) -> dict:
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
    return {
        "Value": {"string": s, "attachmentsByRange": attachments},
        "WFSerializationType": "WFTextTokenString",
    }


def dict_field_items(pairs: list[tuple[str, dict | str]]) -> dict:
    items = []
    for key, val in pairs:
        if isinstance(val, str):
            wf_val = {
                "Value": {"string": val},
                "WFSerializationType": "WFTextTokenString",
            }
        else:
            wf_val = val
        items.append(
            {
                "WFKey": {
                    "Value": {"string": key},
                    "WFSerializationType": "WFTextTokenString",
                },
                "WFItemType": 0,
                "WFValue": wf_val,
            }
        )
    return {
        "Value": {"WFDictionaryFieldValueItems": items},
        "WFSerializationType": "WFDictionaryFieldValue",
    }


def comment(text: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.comment",
        "WFWorkflowActionParameters": {"WFCommentActionText": text},
    }


def set_var_ext(name: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
        "WFWorkflowActionParameters": {
            "WFInput": att({"Type": "ExtensionInput"}),
            "WFVariableName": name,
        },
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


def if_equals_text(var_uuid: str, var_name: str, text: str, group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
        "WFWorkflowActionParameters": {
            "WFInput": {
                "Type": "Variable",
                "Variable": att(
                    {
                        "OutputUUID": var_uuid,
                        "Type": "ActionOutput",
                        "OutputName": var_name,
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
            "WFCondition": 4,
            "WFConditionalActionString": text,
            "GroupingIdentifier": group,
        },
    }


def if_has_value(out_uuid: str, out_name: str, group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.conditional",
        "WFWorkflowActionParameters": {
            "WFInput": {
                "Type": "Variable",
                "Variable": att(
                    {
                        "OutputUUID": out_uuid,
                        "Type": "ActionOutput",
                        "OutputName": out_name,
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
            "WFCondition": 100,
            "GroupingIdentifier": group,
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


def notify(body: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.notification",
        "WFWorkflowActionParameters": {"WFNotificationActionBody": body},
    }


def get_key(from_uuid: str, from_name: str, key: str, out_uuid: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
        "WFWorkflowActionParameters": {
            "WFInput": att(
                {
                    "OutputUUID": from_uuid,
                    "Type": "ActionOutput",
                    "OutputName": from_name,
                }
            ),
            "UUID": out_uuid,
            "WFDictionaryKey": key,
        },
    }


def get_key_from_repeat(key: str, out_uuid: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
        "WFWorkflowActionParameters": {
            "WFInput": att({"Type": "Variable", "VariableName": REPEAT_ITEM}),
            "UUID": out_uuid,
            "WFDictionaryKey": key,
        },
    }


def nichind_post(out_uuid: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": {
            "UUID": out_uuid,
            "ShowHeaders": True,
            "WFURL": NICHIND,
            "WFHTTPMethod": "POST",
            "WFHTTPBodyType": "JSON",
            "WFJSONValues": dict_field_items(
                [("url", text_parts([("var", "inputURL")]))]
            ),
            "WFHTTPHeaders": dict_field_items(
                [
                    ("Accept", "application/json"),
                    ("Content-Type", "application/json"),
                ]
            ),
        },
    }


def repeat_each(list_uuid: str, list_name: str, group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.repeat.each",
        "WFWorkflowActionParameters": {
            "WFInput": att(
                {
                    "OutputUUID": list_uuid,
                    "Type": "ActionOutput",
                    "OutputName": list_name,
                }
            ),
            "GroupingIdentifier": group,
            "WFControlFlowMode": 0,
            "UUID": uid(),
        },
    }


def repeat_end(group: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.repeat.each",
        "WFWorkflowActionParameters": {
            "GroupingIdentifier": group,
            "WFControlFlowMode": 2,
        },
    }


def download_url_from_out(url_uuid: str, url_name: str, out_uuid: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": {
            "ShowHeaders": False,
            "UUID": out_uuid,
            "WFURL": text_parts([("out", url_uuid, url_name)]),
        },
    }


def save_album(from_uuid: str, from_name: str) -> dict:
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.savetocameraroll",
        "WFWorkflowActionParameters": {
            "WFInput": att(
                {
                    "OutputUUID": from_uuid,
                    "Type": "ActionOutput",
                    "OutputName": from_name,
                }
            ),
            "UUID": uid(),
        },
    }


def append_type_download(
    actions: list, type_uuid: str, url_uuid: str, type_name: str
) -> None:
    g = uid()
    dl = uid()
    actions.append(if_equals_text(type_uuid, DICT_VALUE, type_name, g))
    actions.append(download_url_from_out(url_uuid, DICT_VALUE, dl))
    actions.append(save_album(dl, URL_CONTENT))
    actions.append(if_end(g))


def append_nichind_branch(
    actions: list,
    types: list[str],
    ok_msg: str,
    fail_msg: str = "❌ 解析失败或没有对应媒体",
) -> None:
    api_u = uid()
    status_u = uid()
    picker_u = uid()
    if_status = uid()
    if_picker = uid()
    rep = uid()
    type_u = uid()
    url_u = uid()

    actions.append(nichind_post(api_u))
    actions.append(get_key(api_u, URL_CONTENT, "status", status_u))
    actions.append(if_equals_text(status_u, DICT_VALUE, "picker", if_status))
    actions.append(get_key(api_u, URL_CONTENT, "picker", picker_u))
    actions.append(if_has_value(picker_u, DICT_VALUE, if_picker))
    actions.append(repeat_each(picker_u, DICT_VALUE, rep))
    actions.append(get_key_from_repeat("type", type_u))
    actions.append(get_key_from_repeat("url", url_u))
    for t in types:
        append_type_download(actions, type_u, url_u, t)
    actions.append(repeat_end(rep))
    actions.append(notify(ok_msg))
    actions.append(if_else(if_picker))
    actions.append(notify(fail_msg))
    actions.append(if_end(if_picker))
    actions.append(if_else(if_status))

    redirect_u = uid()
    if_redir = uid()
    dl = uid()
    actions.append(get_key(api_u, URL_CONTENT, "url", redirect_u))
    actions.append(if_has_value(redirect_u, DICT_VALUE, if_redir))
    actions.append(download_url_from_out(redirect_u, DICT_VALUE, dl))
    actions.append(save_album(dl, URL_CONTENT))
    actions.append(notify(ok_msg))
    actions.append(if_else(if_redir))
    actions.append(notify(fail_msg))
    actions.append(if_end(if_redir))
    actions.append(if_end(if_status))


def append_single_video_branch(actions: list) -> None:
    api_u = uid()
    status_u = uid()
    picker_u = uid()
    if_status = uid()
    if_picker = uid()
    rep = uid()
    type_u = uid()
    url_u = uid()
    if_video = uid()
    list_u = uid()
    item_u = uid()
    if_item = uid()
    dl = uid()

    actions.append(nichind_post(api_u))
    actions.append(get_key(api_u, URL_CONTENT, "status", status_u))
    actions.append(if_equals_text(status_u, DICT_VALUE, "picker", if_status))
    actions.append(get_key(api_u, URL_CONTENT, "picker", picker_u))
    actions.append(if_has_value(picker_u, DICT_VALUE, if_picker))

    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.list",
            "WFWorkflowActionParameters": {
                "WFItems": [],
                "UUID": list_u,
            },
        }
    )
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
            "WFWorkflowActionParameters": {
                "WFInput": att(
                    {
                        "OutputUUID": list_u,
                        "Type": "ActionOutput",
                        "OutputName": LIST_NAME,
                    }
                ),
                "WFVariableName": "videoURLs",
            },
        }
    )

    actions.append(repeat_each(picker_u, DICT_VALUE, rep))
    actions.append(get_key_from_repeat("type", type_u))
    actions.append(get_key_from_repeat("url", url_u))
    actions.append(if_equals_text(type_u, DICT_VALUE, "video", if_video))
    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.appendvariable",
            "WFWorkflowActionParameters": {
                "WFInput": att(
                    {
                        "OutputUUID": url_u,
                        "Type": "ActionOutput",
                        "OutputName": DICT_VALUE,
                    }
                ),
                "WFVariableName": "videoURLs",
            },
        }
    )
    actions.append(if_end(if_video))
    actions.append(repeat_end(rep))

    actions.append(
        {
            "WFWorkflowActionIdentifier": "is.workflow.actions.getitemfromlist",
            "WFWorkflowActionParameters": {
                "WFInput": att({"Type": "Variable", "VariableName": "videoURLs"}),
                "WFItemSpecifier": "First Item",
                "UUID": item_u,
            },
        }
    )
    actions.append(if_has_value(item_u, LIST_ITEM, if_item))
    actions.append(download_url_from_out(item_u, LIST_ITEM, dl))
    actions.append(save_album(dl, URL_CONTENT))
    actions.append(notify("✅ 单视频已保存"))
    actions.append(if_else(if_item))
    actions.append(notify("❌ 未找到视频"))
    actions.append(if_end(if_item))

    actions.append(if_else(if_picker))
    actions.append(notify("❌ 解析失败"))
    actions.append(if_end(if_picker))
    actions.append(if_else(if_status))
    actions.append(notify("❌ 解析失败"))
    actions.append(if_end(if_status))


def build() -> dict:
    menu = uid()
    actions: list = []

    actions.append(
        comment(
            "X下载·自用（未签名包）\n\n"
            "菜单：默认 / 图片 / 单视频 / 多视频 / GIF\n"
            "主接口：https://dwnld.nichind.dev/\n"
            "（download.nichind.dev 公开 API）\n\n"
            "不用：疯果配置中心、fenguox 私人域名、tvdl 鉴权接口\n"
            "选质：以 nichind 返回为准（图常 4096x4096，视频常最高档）\n\n"
            "导入：未签名，需旧系统中转或 Mac 签名，或在手机上对照重搭。"
        )
    )
    actions.append(set_var_ext("inputURL"))
    actions.append(
        menu_start("选择模式", ["默认", "图片", "单视频", "多视频", "GIF"], menu)
    )

    actions.append(menu_case("默认", menu))
    append_nichind_branch(
        actions,
        types=["photo", "video", "gif"],
        ok_msg="✅ 已保存（默认：自动按类型）",
    )

    actions.append(menu_case("图片", menu))
    append_nichind_branch(actions, types=["photo"], ok_msg="✅ 图片已保存")

    actions.append(menu_case("单视频", menu))
    append_single_video_branch(actions)

    actions.append(menu_case("多视频", menu))
    append_nichind_branch(actions, types=["video"], ok_msg="✅ 视频已保存")

    actions.append(menu_case("GIF", menu))
    append_nichind_branch(
        actions,
        types=["gif"],
        ok_msg="✅ GIF 已保存",
        fail_msg="❌ 未识别到 GIF（若为 mp4 动图请用「单视频」）",
    )

    actions.append(menu_end(menu))

    return {
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


def main() -> None:
    wf = build()
    name = "X-Download"
    shortcut_path = OUT / f"{name}.shortcut"
    with shortcut_path.open("wb") as f:
        plistlib.dump(wf, f, fmt=plistlib.FMT_BINARY)
    with (OUT / f"{name}.plist").open("wb") as f:
        plistlib.dump(wf, f, fmt=plistlib.FMT_XML)
    (OUT / f"{name}.json").write_text(
        json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "README.md").write_text(
        f"""# {name}.shortcut (unsigned)

Chinese display name suggestion: X下载-自用

## Files
- `{name}.shortcut` — unsigned shortcut binary
- `{name}.plist` / `{name}.json` — readable copies

## Flow
Share URL -> choose mode (默认/图片/单视频/多视频/GIF) -> POST nichind -> download by type -> Photos

## Import
iOS 15+ usually cannot import unsigned `.shortcut` directly.
Options: Mac `shortcuts sign`, older device bridge, or rebuild on phone from this logic.

API: `https://dwnld.nichind.dev/`
""",
        encoding="utf-8",
    )
    print("actions:", len(wf["WFWorkflowActions"]))
    print("wrote:", shortcut_path)


if __name__ == "__main__":
    main()
