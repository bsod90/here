{
  "patcher": {
    "fileversion": 1,
    "appversion": {
      "major": 8,
      "minor": 1,
      "revision": 2,
      "architecture": "x64",
      "modernui": 1
    },
    "classnamespace": "box",
    "rect": [
      60.0,
      100.0,
      1400.0,
      900.0
    ],
    "openrect": [
      0.0,
      0.0,
      920.0,
      169.0
    ],
    "bglocked": 0,
    "openinpresentation": 1,
    "default_fontsize": 10.0,
    "default_fontface": 0,
    "default_fontname": "Arial",
    "gridonopen": 1,
    "gridsize": [
      8.0,
      8.0
    ],
    "gridsnaponopen": 1,
    "objectsnaponopen": 1,
    "statusbarvisible": 2,
    "toolbarvisible": 1,
    "lefttoolbarpinned": 0,
    "toptoolbarpinned": 0,
    "righttoolbarpinned": 0,
    "bottomtoolbarpinned": 0,
    "toolbars_unpinned_last_save": 0,
    "tallnewobj": 0,
    "boxanimatetime": 500,
    "enablehscroll": 1,
    "enablevscroll": 1,
    "devicewidth": 920.0,
    "description": "HERE \u2014 MIDI \u2192 OSC controller for the HERE LED installation.",
    "digest": "HERE",
    "tags": "HERE OSC MIDI",
    "style": "",
    "subpatcher_template": "",
    "boxes": [
      {
        "box": {
          "id": "lc-1",
          "maxclass": "live.comment",
          "patching_rect": [
            20.0,
            4.0,
            200.0,
            16.0
          ],
          "text": "HERE \u2014 MIDI \u2192 OSC",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            2.0,
            130.0,
            14.0
          ],
          "fontsize": 10.5,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "n-2",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            40.0,
            60.0,
            22.0
          ],
          "text": "midiin"
        }
      },
      {
        "box": {
          "id": "n-3",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            70.0,
            80.0,
            22.0
          ],
          "text": "midiparse"
        }
      },
      {
        "box": {
          "id": "n-4",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            130.0,
            60.0,
            22.0
          ],
          "text": "midiout"
        }
      },
      {
        "box": {
          "id": "n-5",
          "maxclass": "newobj",
          "patching_rect": [
            120.0,
            100.0,
            100.0,
            22.0
          ],
          "text": "v8 here.js"
        }
      },
      {
        "box": {
          "id": "n-6",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            100.0,
            60.0,
            22.0
          ],
          "text": "pack i i"
        }
      },
      {
        "box": {
          "id": "n-7",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            130.0,
            80.0,
            22.0
          ],
          "text": "prepend note"
        }
      },
      {
        "box": {
          "id": "n-8",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            540.0,
            200.0,
            22.0
          ],
          "text": "udpsend here.local 9000"
        }
      },
      {
        "box": {
          "id": "t-9",
          "maxclass": "live.text",
          "patching_rect": [
            220.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "36",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            20.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_036",
              "parameter_shortname": "36",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-10",
          "maxclass": "live.comment",
          "patching_rect": [
            220.0,
            216.0,
            50.0,
            14.0
          ],
          "text": "Expand",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            36.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Expand"
        }
      },
      {
        "box": {
          "id": "n-11",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-12",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 36 1"
        }
      },
      {
        "box": {
          "id": "n-13",
          "maxclass": "newobj",
          "patching_rect": [
            270.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 36"
        }
      },
      {
        "box": {
          "id": "t-14",
          "maxclass": "live.text",
          "patching_rect": [
            248.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "37",
          "presentation": 1,
          "presentation_rect": [
            33.0,
            20.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_037",
              "parameter_shortname": "37",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-15",
          "maxclass": "live.comment",
          "patching_rect": [
            248.0,
            216.0,
            50.0,
            14.0
          ],
          "text": "Contract",
          "presentation": 1,
          "presentation_rect": [
            33.0,
            36.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Contract"
        }
      },
      {
        "box": {
          "id": "n-16",
          "maxclass": "newobj",
          "patching_rect": [
            248.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-17",
          "maxclass": "newobj",
          "patching_rect": [
            248.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 37 1"
        }
      },
      {
        "box": {
          "id": "n-18",
          "maxclass": "newobj",
          "patching_rect": [
            298.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 37"
        }
      },
      {
        "box": {
          "id": "t-19",
          "maxclass": "live.text",
          "patching_rect": [
            276.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "38",
          "presentation": 1,
          "presentation_rect": [
            60.0,
            20.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_038",
              "parameter_shortname": "38",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-20",
          "maxclass": "live.comment",
          "patching_rect": [
            276.0,
            216.0,
            50.0,
            14.0
          ],
          "text": "Rotate CW",
          "presentation": 1,
          "presentation_rect": [
            60.0,
            36.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Rotate CW"
        }
      },
      {
        "box": {
          "id": "n-21",
          "maxclass": "newobj",
          "patching_rect": [
            276.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-22",
          "maxclass": "newobj",
          "patching_rect": [
            276.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 38 1"
        }
      },
      {
        "box": {
          "id": "n-23",
          "maxclass": "newobj",
          "patching_rect": [
            326.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 38"
        }
      },
      {
        "box": {
          "id": "t-24",
          "maxclass": "live.text",
          "patching_rect": [
            304.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "39",
          "presentation": 1,
          "presentation_rect": [
            87.0,
            20.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_039",
              "parameter_shortname": "39",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-25",
          "maxclass": "live.comment",
          "patching_rect": [
            304.0,
            216.0,
            50.0,
            14.0
          ],
          "text": "Rotate CCW",
          "presentation": 1,
          "presentation_rect": [
            87.0,
            36.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Rotate CCW"
        }
      },
      {
        "box": {
          "id": "n-26",
          "maxclass": "newobj",
          "patching_rect": [
            304.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-27",
          "maxclass": "newobj",
          "patching_rect": [
            304.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 39 1"
        }
      },
      {
        "box": {
          "id": "n-28",
          "maxclass": "newobj",
          "patching_rect": [
            354.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 39"
        }
      },
      {
        "box": {
          "id": "t-29",
          "maxclass": "live.text",
          "patching_rect": [
            332.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "40",
          "presentation": 1,
          "presentation_rect": [
            114.0,
            20.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_040",
              "parameter_shortname": "40",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-30",
          "maxclass": "live.comment",
          "patching_rect": [
            332.0,
            216.0,
            50.0,
            14.0
          ],
          "text": "Pulse",
          "presentation": 1,
          "presentation_rect": [
            114.0,
            36.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Pulse"
        }
      },
      {
        "box": {
          "id": "n-31",
          "maxclass": "newobj",
          "patching_rect": [
            332.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-32",
          "maxclass": "newobj",
          "patching_rect": [
            332.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 40 1"
        }
      },
      {
        "box": {
          "id": "n-33",
          "maxclass": "newobj",
          "patching_rect": [
            382.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 40"
        }
      },
      {
        "box": {
          "id": "t-34",
          "maxclass": "live.text",
          "patching_rect": [
            360.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "41",
          "presentation": 1,
          "presentation_rect": [
            141.0,
            20.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_041",
              "parameter_shortname": "41",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-35",
          "maxclass": "live.comment",
          "patching_rect": [
            360.0,
            216.0,
            50.0,
            14.0
          ],
          "text": "Blow Out",
          "presentation": 1,
          "presentation_rect": [
            141.0,
            36.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Blow Out"
        }
      },
      {
        "box": {
          "id": "n-36",
          "maxclass": "newobj",
          "patching_rect": [
            360.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-37",
          "maxclass": "newobj",
          "patching_rect": [
            360.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 41 1"
        }
      },
      {
        "box": {
          "id": "n-38",
          "maxclass": "newobj",
          "patching_rect": [
            410.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 41"
        }
      },
      {
        "box": {
          "id": "t-39",
          "maxclass": "live.text",
          "patching_rect": [
            388.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "42",
          "presentation": 1,
          "presentation_rect": [
            168.0,
            20.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_042",
              "parameter_shortname": "42",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-40",
          "maxclass": "live.comment",
          "patching_rect": [
            388.0,
            216.0,
            50.0,
            14.0
          ],
          "text": "Regrow",
          "presentation": 1,
          "presentation_rect": [
            168.0,
            36.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Regrow"
        }
      },
      {
        "box": {
          "id": "n-41",
          "maxclass": "newobj",
          "patching_rect": [
            388.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-42",
          "maxclass": "newobj",
          "patching_rect": [
            388.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 42 1"
        }
      },
      {
        "box": {
          "id": "n-43",
          "maxclass": "newobj",
          "patching_rect": [
            438.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 42"
        }
      },
      {
        "box": {
          "id": "t-44",
          "maxclass": "live.text",
          "patching_rect": [
            416.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "43",
          "presentation": 1,
          "presentation_rect": [
            195.0,
            20.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_043",
              "parameter_shortname": "43",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-45",
          "maxclass": "live.comment",
          "patching_rect": [
            416.0,
            216.0,
            50.0,
            14.0
          ],
          "text": "Dissolve",
          "presentation": 1,
          "presentation_rect": [
            195.0,
            36.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Dissolve"
        }
      },
      {
        "box": {
          "id": "n-46",
          "maxclass": "newobj",
          "patching_rect": [
            416.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-47",
          "maxclass": "newobj",
          "patching_rect": [
            416.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 43 1"
        }
      },
      {
        "box": {
          "id": "n-48",
          "maxclass": "newobj",
          "patching_rect": [
            466.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 43"
        }
      },
      {
        "box": {
          "id": "t-49",
          "maxclass": "live.text",
          "patching_rect": [
            444.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "44",
          "presentation": 1,
          "presentation_rect": [
            222.0,
            20.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_044",
              "parameter_shortname": "44",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-50",
          "maxclass": "live.comment",
          "patching_rect": [
            444.0,
            216.0,
            50.0,
            14.0
          ],
          "text": "Respawn",
          "presentation": 1,
          "presentation_rect": [
            222.0,
            36.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Respawn"
        }
      },
      {
        "box": {
          "id": "n-51",
          "maxclass": "newobj",
          "patching_rect": [
            444.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-52",
          "maxclass": "newobj",
          "patching_rect": [
            444.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 44 1"
        }
      },
      {
        "box": {
          "id": "n-53",
          "maxclass": "newobj",
          "patching_rect": [
            494.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 44"
        }
      },
      {
        "box": {
          "id": "t-54",
          "maxclass": "live.text",
          "patching_rect": [
            472.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "45",
          "presentation": 1,
          "presentation_rect": [
            249.0,
            20.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_045",
              "parameter_shortname": "45",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-55",
          "maxclass": "live.comment",
          "patching_rect": [
            472.0,
            216.0,
            50.0,
            14.0
          ],
          "text": "Palette 1",
          "presentation": 1,
          "presentation_rect": [
            249.0,
            36.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Palette 1"
        }
      },
      {
        "box": {
          "id": "n-56",
          "maxclass": "newobj",
          "patching_rect": [
            472.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-57",
          "maxclass": "newobj",
          "patching_rect": [
            472.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 45 1"
        }
      },
      {
        "box": {
          "id": "n-58",
          "maxclass": "newobj",
          "patching_rect": [
            522.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 45"
        }
      },
      {
        "box": {
          "id": "t-59",
          "maxclass": "live.text",
          "patching_rect": [
            220.0,
            230.0,
            24.0,
            14.0
          ],
          "text": "46",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            47.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_046",
              "parameter_shortname": "46",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-60",
          "maxclass": "live.comment",
          "patching_rect": [
            220.0,
            246.0,
            50.0,
            14.0
          ],
          "text": "Palette 2",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            63.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Palette 2"
        }
      },
      {
        "box": {
          "id": "n-61",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            260.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-62",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "note 46 1"
        }
      },
      {
        "box": {
          "id": "n-63",
          "maxclass": "newobj",
          "patching_rect": [
            270.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "noteoff 46"
        }
      },
      {
        "box": {
          "id": "t-64",
          "maxclass": "live.text",
          "patching_rect": [
            248.0,
            230.0,
            24.0,
            14.0
          ],
          "text": "47",
          "presentation": 1,
          "presentation_rect": [
            33.0,
            47.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_047",
              "parameter_shortname": "47",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-65",
          "maxclass": "live.comment",
          "patching_rect": [
            248.0,
            246.0,
            50.0,
            14.0
          ],
          "text": "Palette 3",
          "presentation": 1,
          "presentation_rect": [
            33.0,
            63.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Palette 3"
        }
      },
      {
        "box": {
          "id": "n-66",
          "maxclass": "newobj",
          "patching_rect": [
            248.0,
            260.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-67",
          "maxclass": "newobj",
          "patching_rect": [
            248.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "note 47 1"
        }
      },
      {
        "box": {
          "id": "n-68",
          "maxclass": "newobj",
          "patching_rect": [
            298.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "noteoff 47"
        }
      },
      {
        "box": {
          "id": "t-69",
          "maxclass": "live.text",
          "patching_rect": [
            276.0,
            230.0,
            24.0,
            14.0
          ],
          "text": "48",
          "presentation": 1,
          "presentation_rect": [
            60.0,
            47.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_048",
              "parameter_shortname": "48",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-70",
          "maxclass": "live.comment",
          "patching_rect": [
            276.0,
            246.0,
            50.0,
            14.0
          ],
          "text": "Palette 4",
          "presentation": 1,
          "presentation_rect": [
            60.0,
            63.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Palette 4"
        }
      },
      {
        "box": {
          "id": "n-71",
          "maxclass": "newobj",
          "patching_rect": [
            276.0,
            260.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-72",
          "maxclass": "newobj",
          "patching_rect": [
            276.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "note 48 1"
        }
      },
      {
        "box": {
          "id": "n-73",
          "maxclass": "newobj",
          "patching_rect": [
            326.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "noteoff 48"
        }
      },
      {
        "box": {
          "id": "t-74",
          "maxclass": "live.text",
          "patching_rect": [
            304.0,
            230.0,
            24.0,
            14.0
          ],
          "text": "49",
          "presentation": 1,
          "presentation_rect": [
            87.0,
            47.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_049",
              "parameter_shortname": "49",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-75",
          "maxclass": "live.comment",
          "patching_rect": [
            304.0,
            246.0,
            50.0,
            14.0
          ],
          "text": "Push L",
          "presentation": 1,
          "presentation_rect": [
            87.0,
            63.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Push L"
        }
      },
      {
        "box": {
          "id": "n-76",
          "maxclass": "newobj",
          "patching_rect": [
            304.0,
            260.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-77",
          "maxclass": "newobj",
          "patching_rect": [
            304.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "note 49 1"
        }
      },
      {
        "box": {
          "id": "n-78",
          "maxclass": "newobj",
          "patching_rect": [
            354.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "noteoff 49"
        }
      },
      {
        "box": {
          "id": "t-79",
          "maxclass": "live.text",
          "patching_rect": [
            332.0,
            230.0,
            24.0,
            14.0
          ],
          "text": "50",
          "presentation": 1,
          "presentation_rect": [
            114.0,
            47.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_050",
              "parameter_shortname": "50",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-80",
          "maxclass": "live.comment",
          "patching_rect": [
            332.0,
            246.0,
            50.0,
            14.0
          ],
          "text": "Push R",
          "presentation": 1,
          "presentation_rect": [
            114.0,
            63.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Push R"
        }
      },
      {
        "box": {
          "id": "n-81",
          "maxclass": "newobj",
          "patching_rect": [
            332.0,
            260.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-82",
          "maxclass": "newobj",
          "patching_rect": [
            332.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "note 50 1"
        }
      },
      {
        "box": {
          "id": "n-83",
          "maxclass": "newobj",
          "patching_rect": [
            382.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "noteoff 50"
        }
      },
      {
        "box": {
          "id": "t-84",
          "maxclass": "live.text",
          "patching_rect": [
            360.0,
            230.0,
            24.0,
            14.0
          ],
          "text": "51",
          "presentation": 1,
          "presentation_rect": [
            141.0,
            47.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_051",
              "parameter_shortname": "51",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-85",
          "maxclass": "live.comment",
          "patching_rect": [
            360.0,
            246.0,
            50.0,
            14.0
          ],
          "text": "Push U",
          "presentation": 1,
          "presentation_rect": [
            141.0,
            63.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Push U"
        }
      },
      {
        "box": {
          "id": "n-86",
          "maxclass": "newobj",
          "patching_rect": [
            360.0,
            260.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-87",
          "maxclass": "newobj",
          "patching_rect": [
            360.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "note 51 1"
        }
      },
      {
        "box": {
          "id": "n-88",
          "maxclass": "newobj",
          "patching_rect": [
            410.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "noteoff 51"
        }
      },
      {
        "box": {
          "id": "t-89",
          "maxclass": "live.text",
          "patching_rect": [
            388.0,
            230.0,
            24.0,
            14.0
          ],
          "text": "52",
          "presentation": 1,
          "presentation_rect": [
            168.0,
            47.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_052",
              "parameter_shortname": "52",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-90",
          "maxclass": "live.comment",
          "patching_rect": [
            388.0,
            246.0,
            50.0,
            14.0
          ],
          "text": "Push D",
          "presentation": 1,
          "presentation_rect": [
            168.0,
            63.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Push D"
        }
      },
      {
        "box": {
          "id": "n-91",
          "maxclass": "newobj",
          "patching_rect": [
            388.0,
            260.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-92",
          "maxclass": "newobj",
          "patching_rect": [
            388.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "note 52 1"
        }
      },
      {
        "box": {
          "id": "n-93",
          "maxclass": "newobj",
          "patching_rect": [
            438.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "noteoff 52"
        }
      },
      {
        "box": {
          "id": "t-94",
          "maxclass": "live.text",
          "patching_rect": [
            416.0,
            230.0,
            24.0,
            14.0
          ],
          "text": "53",
          "presentation": 1,
          "presentation_rect": [
            195.0,
            47.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_053",
              "parameter_shortname": "53",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-95",
          "maxclass": "live.comment",
          "patching_rect": [
            416.0,
            246.0,
            50.0,
            14.0
          ],
          "text": "Pull Center",
          "presentation": 1,
          "presentation_rect": [
            195.0,
            63.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Pull Center"
        }
      },
      {
        "box": {
          "id": "n-96",
          "maxclass": "newobj",
          "patching_rect": [
            416.0,
            260.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-97",
          "maxclass": "newobj",
          "patching_rect": [
            416.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "note 53 1"
        }
      },
      {
        "box": {
          "id": "n-98",
          "maxclass": "newobj",
          "patching_rect": [
            466.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "noteoff 53"
        }
      },
      {
        "box": {
          "id": "t-99",
          "maxclass": "live.text",
          "patching_rect": [
            444.0,
            230.0,
            24.0,
            14.0
          ],
          "text": "54",
          "presentation": 1,
          "presentation_rect": [
            222.0,
            47.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_054",
              "parameter_shortname": "54",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-100",
          "maxclass": "live.comment",
          "patching_rect": [
            444.0,
            246.0,
            50.0,
            14.0
          ],
          "text": "Outer CW",
          "presentation": 1,
          "presentation_rect": [
            222.0,
            63.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Outer CW"
        }
      },
      {
        "box": {
          "id": "n-101",
          "maxclass": "newobj",
          "patching_rect": [
            444.0,
            260.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-102",
          "maxclass": "newobj",
          "patching_rect": [
            444.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "note 54 1"
        }
      },
      {
        "box": {
          "id": "n-103",
          "maxclass": "newobj",
          "patching_rect": [
            494.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "noteoff 54"
        }
      },
      {
        "box": {
          "id": "t-104",
          "maxclass": "live.text",
          "patching_rect": [
            472.0,
            230.0,
            24.0,
            14.0
          ],
          "text": "55",
          "presentation": 1,
          "presentation_rect": [
            249.0,
            47.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_055",
              "parameter_shortname": "55",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-105",
          "maxclass": "live.comment",
          "patching_rect": [
            472.0,
            246.0,
            50.0,
            14.0
          ],
          "text": "Outer CCW",
          "presentation": 1,
          "presentation_rect": [
            249.0,
            63.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Outer CCW"
        }
      },
      {
        "box": {
          "id": "n-106",
          "maxclass": "newobj",
          "patching_rect": [
            472.0,
            260.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-107",
          "maxclass": "newobj",
          "patching_rect": [
            472.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "note 55 1"
        }
      },
      {
        "box": {
          "id": "n-108",
          "maxclass": "newobj",
          "patching_rect": [
            522.0,
            290.0,
            100.0,
            22.0
          ],
          "text": "noteoff 55"
        }
      },
      {
        "box": {
          "id": "t-109",
          "maxclass": "live.text",
          "patching_rect": [
            220.0,
            260.0,
            24.0,
            14.0
          ],
          "text": "56",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            74.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_056",
              "parameter_shortname": "56",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-110",
          "maxclass": "live.comment",
          "patching_rect": [
            220.0,
            276.0,
            50.0,
            14.0
          ],
          "text": "Middle CW",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            90.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Middle CW"
        }
      },
      {
        "box": {
          "id": "n-111",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            290.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-112",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "note 56 1"
        }
      },
      {
        "box": {
          "id": "n-113",
          "maxclass": "newobj",
          "patching_rect": [
            270.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "noteoff 56"
        }
      },
      {
        "box": {
          "id": "t-114",
          "maxclass": "live.text",
          "patching_rect": [
            248.0,
            260.0,
            24.0,
            14.0
          ],
          "text": "57",
          "presentation": 1,
          "presentation_rect": [
            33.0,
            74.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_057",
              "parameter_shortname": "57",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-115",
          "maxclass": "live.comment",
          "patching_rect": [
            248.0,
            276.0,
            50.0,
            14.0
          ],
          "text": "Middle CCW",
          "presentation": 1,
          "presentation_rect": [
            33.0,
            90.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Middle CCW"
        }
      },
      {
        "box": {
          "id": "n-116",
          "maxclass": "newobj",
          "patching_rect": [
            248.0,
            290.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-117",
          "maxclass": "newobj",
          "patching_rect": [
            248.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "note 57 1"
        }
      },
      {
        "box": {
          "id": "n-118",
          "maxclass": "newobj",
          "patching_rect": [
            298.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "noteoff 57"
        }
      },
      {
        "box": {
          "id": "t-119",
          "maxclass": "live.text",
          "patching_rect": [
            276.0,
            260.0,
            24.0,
            14.0
          ],
          "text": "58",
          "presentation": 1,
          "presentation_rect": [
            60.0,
            74.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_058",
              "parameter_shortname": "58",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-120",
          "maxclass": "live.comment",
          "patching_rect": [
            276.0,
            276.0,
            50.0,
            14.0
          ],
          "text": "Inner CW",
          "presentation": 1,
          "presentation_rect": [
            60.0,
            90.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Inner CW"
        }
      },
      {
        "box": {
          "id": "n-121",
          "maxclass": "newobj",
          "patching_rect": [
            276.0,
            290.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-122",
          "maxclass": "newobj",
          "patching_rect": [
            276.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "note 58 1"
        }
      },
      {
        "box": {
          "id": "n-123",
          "maxclass": "newobj",
          "patching_rect": [
            326.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "noteoff 58"
        }
      },
      {
        "box": {
          "id": "t-124",
          "maxclass": "live.text",
          "patching_rect": [
            304.0,
            260.0,
            24.0,
            14.0
          ],
          "text": "59",
          "presentation": 1,
          "presentation_rect": [
            87.0,
            74.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_059",
              "parameter_shortname": "59",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-125",
          "maxclass": "live.comment",
          "patching_rect": [
            304.0,
            276.0,
            50.0,
            14.0
          ],
          "text": "Inner CCW",
          "presentation": 1,
          "presentation_rect": [
            87.0,
            90.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Inner CCW"
        }
      },
      {
        "box": {
          "id": "n-126",
          "maxclass": "newobj",
          "patching_rect": [
            304.0,
            290.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-127",
          "maxclass": "newobj",
          "patching_rect": [
            304.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "note 59 1"
        }
      },
      {
        "box": {
          "id": "n-128",
          "maxclass": "newobj",
          "patching_rect": [
            354.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "noteoff 59"
        }
      },
      {
        "box": {
          "id": "t-129",
          "maxclass": "live.text",
          "patching_rect": [
            332.0,
            260.0,
            24.0,
            14.0
          ],
          "text": "60",
          "presentation": 1,
          "presentation_rect": [
            114.0,
            74.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_060",
              "parameter_shortname": "60",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-130",
          "maxclass": "live.comment",
          "patching_rect": [
            332.0,
            276.0,
            50.0,
            14.0
          ],
          "text": "Stop Rot All",
          "presentation": 1,
          "presentation_rect": [
            114.0,
            90.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Stop Rot All"
        }
      },
      {
        "box": {
          "id": "n-131",
          "maxclass": "newobj",
          "patching_rect": [
            332.0,
            290.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-132",
          "maxclass": "newobj",
          "patching_rect": [
            332.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "note 60 1"
        }
      },
      {
        "box": {
          "id": "n-133",
          "maxclass": "newobj",
          "patching_rect": [
            382.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "noteoff 60"
        }
      },
      {
        "box": {
          "id": "t-134",
          "maxclass": "live.text",
          "patching_rect": [
            360.0,
            260.0,
            24.0,
            14.0
          ],
          "text": "61",
          "presentation": 1,
          "presentation_rect": [
            141.0,
            74.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_061",
              "parameter_shortname": "61",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-135",
          "maxclass": "live.comment",
          "patching_rect": [
            360.0,
            276.0,
            50.0,
            14.0
          ],
          "text": "Stop Outer",
          "presentation": 1,
          "presentation_rect": [
            141.0,
            90.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Stop Outer"
        }
      },
      {
        "box": {
          "id": "n-136",
          "maxclass": "newobj",
          "patching_rect": [
            360.0,
            290.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-137",
          "maxclass": "newobj",
          "patching_rect": [
            360.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "note 61 1"
        }
      },
      {
        "box": {
          "id": "n-138",
          "maxclass": "newobj",
          "patching_rect": [
            410.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "noteoff 61"
        }
      },
      {
        "box": {
          "id": "t-139",
          "maxclass": "live.text",
          "patching_rect": [
            388.0,
            260.0,
            24.0,
            14.0
          ],
          "text": "62",
          "presentation": 1,
          "presentation_rect": [
            168.0,
            74.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_062",
              "parameter_shortname": "62",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-140",
          "maxclass": "live.comment",
          "patching_rect": [
            388.0,
            276.0,
            50.0,
            14.0
          ],
          "text": "Stop Middle",
          "presentation": 1,
          "presentation_rect": [
            168.0,
            90.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Stop Middle"
        }
      },
      {
        "box": {
          "id": "n-141",
          "maxclass": "newobj",
          "patching_rect": [
            388.0,
            290.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-142",
          "maxclass": "newobj",
          "patching_rect": [
            388.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "note 62 1"
        }
      },
      {
        "box": {
          "id": "n-143",
          "maxclass": "newobj",
          "patching_rect": [
            438.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "noteoff 62"
        }
      },
      {
        "box": {
          "id": "t-144",
          "maxclass": "live.text",
          "patching_rect": [
            416.0,
            260.0,
            24.0,
            14.0
          ],
          "text": "63",
          "presentation": 1,
          "presentation_rect": [
            195.0,
            74.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_063",
              "parameter_shortname": "63",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-145",
          "maxclass": "live.comment",
          "patching_rect": [
            416.0,
            276.0,
            50.0,
            14.0
          ],
          "text": "Stop Inner",
          "presentation": 1,
          "presentation_rect": [
            195.0,
            90.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Stop Inner"
        }
      },
      {
        "box": {
          "id": "n-146",
          "maxclass": "newobj",
          "patching_rect": [
            416.0,
            290.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-147",
          "maxclass": "newobj",
          "patching_rect": [
            416.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "note 63 1"
        }
      },
      {
        "box": {
          "id": "n-148",
          "maxclass": "newobj",
          "patching_rect": [
            466.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "noteoff 63"
        }
      },
      {
        "box": {
          "id": "t-149",
          "maxclass": "live.text",
          "patching_rect": [
            444.0,
            260.0,
            24.0,
            14.0
          ],
          "text": "64",
          "presentation": 1,
          "presentation_rect": [
            222.0,
            74.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_064",
              "parameter_shortname": "64",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-150",
          "maxclass": "live.comment",
          "patching_rect": [
            444.0,
            276.0,
            50.0,
            14.0
          ],
          "text": "Push Random",
          "presentation": 1,
          "presentation_rect": [
            222.0,
            90.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Push Random"
        }
      },
      {
        "box": {
          "id": "n-151",
          "maxclass": "newobj",
          "patching_rect": [
            444.0,
            290.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-152",
          "maxclass": "newobj",
          "patching_rect": [
            444.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "note 64 1"
        }
      },
      {
        "box": {
          "id": "n-153",
          "maxclass": "newobj",
          "patching_rect": [
            494.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "noteoff 64"
        }
      },
      {
        "box": {
          "id": "t-154",
          "maxclass": "live.text",
          "patching_rect": [
            472.0,
            260.0,
            24.0,
            14.0
          ],
          "text": "65",
          "presentation": 1,
          "presentation_rect": [
            249.0,
            74.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_065",
              "parameter_shortname": "65",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-155",
          "maxclass": "live.comment",
          "patching_rect": [
            472.0,
            276.0,
            50.0,
            14.0
          ],
          "text": "Show Outer",
          "presentation": 1,
          "presentation_rect": [
            249.0,
            90.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Show Outer"
        }
      },
      {
        "box": {
          "id": "n-156",
          "maxclass": "newobj",
          "patching_rect": [
            472.0,
            290.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-157",
          "maxclass": "newobj",
          "patching_rect": [
            472.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "note 65 1"
        }
      },
      {
        "box": {
          "id": "n-158",
          "maxclass": "newobj",
          "patching_rect": [
            522.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "noteoff 65"
        }
      },
      {
        "box": {
          "id": "t-159",
          "maxclass": "live.text",
          "patching_rect": [
            220.0,
            290.0,
            24.0,
            14.0
          ],
          "text": "66",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            101.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_066",
              "parameter_shortname": "66",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-160",
          "maxclass": "live.comment",
          "patching_rect": [
            220.0,
            306.0,
            50.0,
            14.0
          ],
          "text": "Hide Outer",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            117.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Hide Outer"
        }
      },
      {
        "box": {
          "id": "n-161",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            320.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-162",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "note 66 1"
        }
      },
      {
        "box": {
          "id": "n-163",
          "maxclass": "newobj",
          "patching_rect": [
            270.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "noteoff 66"
        }
      },
      {
        "box": {
          "id": "t-164",
          "maxclass": "live.text",
          "patching_rect": [
            248.0,
            290.0,
            24.0,
            14.0
          ],
          "text": "67",
          "presentation": 1,
          "presentation_rect": [
            33.0,
            101.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_067",
              "parameter_shortname": "67",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-165",
          "maxclass": "live.comment",
          "patching_rect": [
            248.0,
            306.0,
            50.0,
            14.0
          ],
          "text": "Show Middle",
          "presentation": 1,
          "presentation_rect": [
            33.0,
            117.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Show Middle"
        }
      },
      {
        "box": {
          "id": "n-166",
          "maxclass": "newobj",
          "patching_rect": [
            248.0,
            320.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-167",
          "maxclass": "newobj",
          "patching_rect": [
            248.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "note 67 1"
        }
      },
      {
        "box": {
          "id": "n-168",
          "maxclass": "newobj",
          "patching_rect": [
            298.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "noteoff 67"
        }
      },
      {
        "box": {
          "id": "t-169",
          "maxclass": "live.text",
          "patching_rect": [
            276.0,
            290.0,
            24.0,
            14.0
          ],
          "text": "68",
          "presentation": 1,
          "presentation_rect": [
            60.0,
            101.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_068",
              "parameter_shortname": "68",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-170",
          "maxclass": "live.comment",
          "patching_rect": [
            276.0,
            306.0,
            50.0,
            14.0
          ],
          "text": "Hide Middle",
          "presentation": 1,
          "presentation_rect": [
            60.0,
            117.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Hide Middle"
        }
      },
      {
        "box": {
          "id": "n-171",
          "maxclass": "newobj",
          "patching_rect": [
            276.0,
            320.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-172",
          "maxclass": "newobj",
          "patching_rect": [
            276.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "note 68 1"
        }
      },
      {
        "box": {
          "id": "n-173",
          "maxclass": "newobj",
          "patching_rect": [
            326.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "noteoff 68"
        }
      },
      {
        "box": {
          "id": "t-174",
          "maxclass": "live.text",
          "patching_rect": [
            304.0,
            290.0,
            24.0,
            14.0
          ],
          "text": "69",
          "presentation": 1,
          "presentation_rect": [
            87.0,
            101.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_069",
              "parameter_shortname": "69",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-175",
          "maxclass": "live.comment",
          "patching_rect": [
            304.0,
            306.0,
            50.0,
            14.0
          ],
          "text": "Show Inner",
          "presentation": 1,
          "presentation_rect": [
            87.0,
            117.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Show Inner"
        }
      },
      {
        "box": {
          "id": "n-176",
          "maxclass": "newobj",
          "patching_rect": [
            304.0,
            320.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-177",
          "maxclass": "newobj",
          "patching_rect": [
            304.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "note 69 1"
        }
      },
      {
        "box": {
          "id": "n-178",
          "maxclass": "newobj",
          "patching_rect": [
            354.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "noteoff 69"
        }
      },
      {
        "box": {
          "id": "t-179",
          "maxclass": "live.text",
          "patching_rect": [
            332.0,
            290.0,
            24.0,
            14.0
          ],
          "text": "70",
          "presentation": 1,
          "presentation_rect": [
            114.0,
            101.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_070",
              "parameter_shortname": "70",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-180",
          "maxclass": "live.comment",
          "patching_rect": [
            332.0,
            306.0,
            50.0,
            14.0
          ],
          "text": "Hide Inner",
          "presentation": 1,
          "presentation_rect": [
            114.0,
            117.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Hide Inner"
        }
      },
      {
        "box": {
          "id": "n-181",
          "maxclass": "newobj",
          "patching_rect": [
            332.0,
            320.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-182",
          "maxclass": "newobj",
          "patching_rect": [
            332.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "note 70 1"
        }
      },
      {
        "box": {
          "id": "n-183",
          "maxclass": "newobj",
          "patching_rect": [
            382.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "noteoff 70"
        }
      },
      {
        "box": {
          "id": "t-184",
          "maxclass": "live.text",
          "patching_rect": [
            360.0,
            290.0,
            24.0,
            14.0
          ],
          "text": "71",
          "presentation": 1,
          "presentation_rect": [
            141.0,
            101.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_071",
              "parameter_shortname": "71",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-185",
          "maxclass": "live.comment",
          "patching_rect": [
            360.0,
            306.0,
            50.0,
            14.0
          ],
          "text": "Meteors",
          "presentation": 1,
          "presentation_rect": [
            141.0,
            117.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Meteors"
        }
      },
      {
        "box": {
          "id": "n-186",
          "maxclass": "newobj",
          "patching_rect": [
            360.0,
            320.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-187",
          "maxclass": "newobj",
          "patching_rect": [
            360.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "note 71 1"
        }
      },
      {
        "box": {
          "id": "n-188",
          "maxclass": "newobj",
          "patching_rect": [
            410.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "noteoff 71"
        }
      },
      {
        "box": {
          "id": "t-189",
          "maxclass": "live.text",
          "patching_rect": [
            388.0,
            290.0,
            24.0,
            14.0
          ],
          "text": "72",
          "presentation": 1,
          "presentation_rect": [
            168.0,
            101.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_072",
              "parameter_shortname": "72",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-190",
          "maxclass": "live.comment",
          "patching_rect": [
            388.0,
            306.0,
            50.0,
            14.0
          ],
          "text": "Dust",
          "presentation": 1,
          "presentation_rect": [
            168.0,
            117.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Dust"
        }
      },
      {
        "box": {
          "id": "n-191",
          "maxclass": "newobj",
          "patching_rect": [
            388.0,
            320.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-192",
          "maxclass": "newobj",
          "patching_rect": [
            388.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "note 72 1"
        }
      },
      {
        "box": {
          "id": "n-193",
          "maxclass": "newobj",
          "patching_rect": [
            438.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "noteoff 72"
        }
      },
      {
        "box": {
          "id": "t-194",
          "maxclass": "live.text",
          "patching_rect": [
            416.0,
            290.0,
            24.0,
            14.0
          ],
          "text": "73",
          "presentation": 1,
          "presentation_rect": [
            195.0,
            101.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_073",
              "parameter_shortname": "73",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-195",
          "maxclass": "live.comment",
          "patching_rect": [
            416.0,
            306.0,
            50.0,
            14.0
          ],
          "text": "Flash",
          "presentation": 1,
          "presentation_rect": [
            195.0,
            117.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Flash"
        }
      },
      {
        "box": {
          "id": "n-196",
          "maxclass": "newobj",
          "patching_rect": [
            416.0,
            320.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-197",
          "maxclass": "newobj",
          "patching_rect": [
            416.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "note 73 1"
        }
      },
      {
        "box": {
          "id": "n-198",
          "maxclass": "newobj",
          "patching_rect": [
            466.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "noteoff 73"
        }
      },
      {
        "box": {
          "id": "t-199",
          "maxclass": "live.text",
          "patching_rect": [
            444.0,
            290.0,
            24.0,
            14.0
          ],
          "text": "74",
          "presentation": 1,
          "presentation_rect": [
            222.0,
            101.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_074",
              "parameter_shortname": "74",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-200",
          "maxclass": "live.comment",
          "patching_rect": [
            444.0,
            306.0,
            50.0,
            14.0
          ],
          "text": "Wipe",
          "presentation": 1,
          "presentation_rect": [
            222.0,
            117.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Wipe"
        }
      },
      {
        "box": {
          "id": "n-201",
          "maxclass": "newobj",
          "patching_rect": [
            444.0,
            320.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-202",
          "maxclass": "newobj",
          "patching_rect": [
            444.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "note 74 1"
        }
      },
      {
        "box": {
          "id": "n-203",
          "maxclass": "newobj",
          "patching_rect": [
            494.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "noteoff 74"
        }
      },
      {
        "box": {
          "id": "t-204",
          "maxclass": "live.text",
          "patching_rect": [
            472.0,
            290.0,
            24.0,
            14.0
          ],
          "text": "75",
          "presentation": 1,
          "presentation_rect": [
            249.0,
            101.0,
            26.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 2,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_075",
              "parameter_shortname": "75",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-205",
          "maxclass": "live.comment",
          "patching_rect": [
            472.0,
            306.0,
            50.0,
            14.0
          ],
          "text": "Shimmer",
          "presentation": 1,
          "presentation_rect": [
            249.0,
            117.0,
            26.0,
            10.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Shimmer"
        }
      },
      {
        "box": {
          "id": "n-206",
          "maxclass": "newobj",
          "patching_rect": [
            472.0,
            320.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "n-207",
          "maxclass": "newobj",
          "patching_rect": [
            472.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "note 75 1"
        }
      },
      {
        "box": {
          "id": "n-208",
          "maxclass": "newobj",
          "patching_rect": [
            522.0,
            350.0,
            100.0,
            22.0
          ],
          "text": "noteoff 75"
        }
      },
      {
        "box": {
          "id": "d-209",
          "maxclass": "live.dial",
          "patching_rect": [
            420.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            290.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                2.5
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_radius_min",
              "parameter_shortname": "Radius Min",
              "parameter_mmax": 12.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-210",
          "maxclass": "live.comment",
          "patching_rect": [
            420.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Radius Min",
          "presentation": 1,
          "presentation_rect": [
            290.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Radius Min"
        }
      },
      {
        "box": {
          "id": "n-211",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-212",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master radius_min"
        }
      },
      {
        "box": {
          "id": "d-213",
          "maxclass": "live.dial",
          "patching_rect": [
            456.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            320.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                16.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_radius_max",
              "parameter_shortname": "Radius Max",
              "parameter_mmax": 22.0,
              "parameter_mmin": 8.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-214",
          "maxclass": "live.comment",
          "patching_rect": [
            456.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Radius Max",
          "presentation": 1,
          "presentation_rect": [
            320.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Radius Max"
        }
      },
      {
        "box": {
          "id": "n-215",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-216",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master radius_max"
        }
      },
      {
        "box": {
          "id": "d-217",
          "maxclass": "live.dial",
          "patching_rect": [
            492.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            350.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                8.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_radius_default",
              "parameter_shortname": "Radius Defa",
              "parameter_mmax": 20.0,
              "parameter_mmin": 2.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-218",
          "maxclass": "live.comment",
          "patching_rect": [
            492.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Radius Default",
          "presentation": 1,
          "presentation_rect": [
            350.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Radius Default"
        }
      },
      {
        "box": {
          "id": "n-219",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-220",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master radius_default"
        }
      },
      {
        "box": {
          "id": "d-221",
          "maxclass": "live.dial",
          "patching_rect": [
            528.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            380.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_brightness",
              "parameter_shortname": "Brightness",
              "parameter_mmax": 2.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-222",
          "maxclass": "live.comment",
          "patching_rect": [
            528.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Brightness",
          "presentation": 1,
          "presentation_rect": [
            380.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Brightness"
        }
      },
      {
        "box": {
          "id": "n-223",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-224",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master brightness"
        }
      },
      {
        "box": {
          "id": "d-225",
          "maxclass": "live.dial",
          "patching_rect": [
            564.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            410.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_gap_coefficient",
              "parameter_shortname": "Ring Gap",
              "parameter_mmax": 6.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-226",
          "maxclass": "live.comment",
          "patching_rect": [
            564.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Ring Gap",
          "presentation": 1,
          "presentation_rect": [
            410.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Ring Gap"
        }
      },
      {
        "box": {
          "id": "n-227",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-228",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master gap_coefficient"
        }
      },
      {
        "box": {
          "id": "d-229",
          "maxclass": "live.dial",
          "patching_rect": [
            600.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            440.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                2.5
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_dot_orbit_speed",
              "parameter_shortname": "Comet Spin",
              "parameter_mmax": 8.0,
              "parameter_mmin": 0.5,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-230",
          "maxclass": "live.comment",
          "patching_rect": [
            600.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Comet Spin",
          "presentation": 1,
          "presentation_rect": [
            440.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Comet Spin"
        }
      },
      {
        "box": {
          "id": "n-231",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-232",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master dot_orbit_speed"
        }
      },
      {
        "box": {
          "id": "d-233",
          "maxclass": "live.dial",
          "patching_rect": [
            636.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            470.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                14.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_trail_steps",
              "parameter_shortname": "Tail Length",
              "parameter_mmax": 40.0,
              "parameter_mmin": 4.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-234",
          "maxclass": "live.comment",
          "patching_rect": [
            636.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Tail Length",
          "presentation": 1,
          "presentation_rect": [
            470.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Tail Length"
        }
      },
      {
        "box": {
          "id": "n-235",
          "maxclass": "newobj",
          "patching_rect": [
            636.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-236",
          "maxclass": "newobj",
          "patching_rect": [
            636.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master trail_steps"
        }
      },
      {
        "box": {
          "id": "d-237",
          "maxclass": "live.dial",
          "patching_rect": [
            672.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            500.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.1
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_dot_speed_min",
              "parameter_shortname": "Speed Min",
              "parameter_mmax": 1.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-238",
          "maxclass": "live.comment",
          "patching_rect": [
            672.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Speed Min",
          "presentation": 1,
          "presentation_rect": [
            500.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Speed Min"
        }
      },
      {
        "box": {
          "id": "n-239",
          "maxclass": "newobj",
          "patching_rect": [
            672.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-240",
          "maxclass": "newobj",
          "patching_rect": [
            672.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master dot_speed_min"
        }
      },
      {
        "box": {
          "id": "d-241",
          "maxclass": "live.dial",
          "patching_rect": [
            708.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            530.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.3
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_dot_speed_max",
              "parameter_shortname": "Speed Max",
              "parameter_mmax": 2.5,
              "parameter_mmin": 0.3,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-242",
          "maxclass": "live.comment",
          "patching_rect": [
            708.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Speed Max",
          "presentation": 1,
          "presentation_rect": [
            530.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Speed Max"
        }
      },
      {
        "box": {
          "id": "n-243",
          "maxclass": "newobj",
          "patching_rect": [
            708.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-244",
          "maxclass": "newobj",
          "patching_rect": [
            708.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master dot_speed_max"
        }
      },
      {
        "box": {
          "id": "d-245",
          "maxclass": "live.dial",
          "patching_rect": [
            744.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            560.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.6
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_dot_speed_lock_exp",
              "parameter_shortname": "Speed Curve",
              "parameter_mmax": 4.0,
              "parameter_mmin": 0.3,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-246",
          "maxclass": "live.comment",
          "patching_rect": [
            744.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Speed Curve",
          "presentation": 1,
          "presentation_rect": [
            560.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Speed Curve"
        }
      },
      {
        "box": {
          "id": "n-247",
          "maxclass": "newobj",
          "patching_rect": [
            744.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-248",
          "maxclass": "newobj",
          "patching_rect": [
            744.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master dot_speed_lock_exp"
        }
      },
      {
        "box": {
          "id": "d-249",
          "maxclass": "live.dial",
          "patching_rect": [
            780.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            590.0,
            20.0,
            28.0,
            28.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.18
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_shimmer_intensity",
              "parameter_shortname": "Shimmer Amp",
              "parameter_mmax": 0.6,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-250",
          "maxclass": "live.comment",
          "patching_rect": [
            780.0,
            738.0,
            40.0,
            12.0
          ],
          "text": "Shimmer Amp",
          "presentation": 1,
          "presentation_rect": [
            590.0,
            49.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Shimmer Amp"
        }
      },
      {
        "box": {
          "id": "n-251",
          "maxclass": "newobj",
          "patching_rect": [
            780.0,
            760.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-252",
          "maxclass": "newobj",
          "patching_rect": [
            780.0,
            790.0,
            180.0,
            22.0
          ],
          "text": "prepend knob master shimmer_intensity"
        }
      },
      {
        "box": {
          "id": "lc-253",
          "maxclass": "live.comment",
          "patching_rect": [
            360.0,
            800.0,
            50.0,
            14.0
          ],
          "text": "Outer",
          "presentation": 1,
          "presentation_rect": [
            258.0,
            64.0,
            30.0,
            18.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Outer ring"
        }
      },
      {
        "box": {
          "id": "d-254",
          "maxclass": "live.dial",
          "patching_rect": [
            420.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            290.0,
            64.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.12
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_skew_0",
              "parameter_shortname": "O Skew",
              "parameter_mmax": 0.5,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-255",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-256",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            844.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 0 skew"
        }
      },
      {
        "box": {
          "id": "d-257",
          "maxclass": "live.dial",
          "patching_rect": [
            456.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            320.0,
            64.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_phase_0",
              "parameter_shortname": "O Phase",
              "parameter_mmax": 3.14159,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-258",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-259",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            844.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 0 phase"
        }
      },
      {
        "box": {
          "id": "d-260",
          "maxclass": "live.dial",
          "patching_rect": [
            492.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            350.0,
            64.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.8
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_blur_0",
              "parameter_shortname": "O Blur",
              "parameter_mmax": 8.0,
              "parameter_mmin": 0.3,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-261",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-262",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            844.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 0 blur"
        }
      },
      {
        "box": {
          "id": "d-263",
          "maxclass": "live.dial",
          "patching_rect": [
            528.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            380.0,
            64.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_radius_scale_0",
              "parameter_shortname": "O Scale",
              "parameter_mmax": 2.0,
              "parameter_mmin": 0.2,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-264",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-265",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            844.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 0 radius_scale"
        }
      },
      {
        "box": {
          "id": "d-266",
          "maxclass": "live.dial",
          "patching_rect": [
            564.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            410.0,
            64.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_segments_0",
              "parameter_shortname": "O Dash",
              "parameter_mmax": 32.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-267",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-268",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            844.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 0 segments"
        }
      },
      {
        "box": {
          "id": "d-269",
          "maxclass": "live.dial",
          "patching_rect": [
            600.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            440.0,
            64.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.4
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_gap_0",
              "parameter_shortname": "O Gap",
              "parameter_mmax": 0.95,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-270",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-271",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            844.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 0 gap"
        }
      },
      {
        "box": {
          "id": "lc-272",
          "maxclass": "live.comment",
          "patching_rect": [
            360.0,
            830.0,
            50.0,
            14.0
          ],
          "text": "Middle",
          "presentation": 1,
          "presentation_rect": [
            258.0,
            86.0,
            30.0,
            18.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Middle ring"
        }
      },
      {
        "box": {
          "id": "d-273",
          "maxclass": "live.dial",
          "patching_rect": [
            420.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            290.0,
            86.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.18
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_skew_1",
              "parameter_shortname": "M Skew",
              "parameter_mmax": 0.5,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-274",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-275",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            924.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 1 skew"
        }
      },
      {
        "box": {
          "id": "d-276",
          "maxclass": "live.dial",
          "patching_rect": [
            456.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            320.0,
            86.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_phase_1",
              "parameter_shortname": "M Phase",
              "parameter_mmax": 3.14159,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-277",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-278",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            924.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 1 phase"
        }
      },
      {
        "box": {
          "id": "d-279",
          "maxclass": "live.dial",
          "patching_rect": [
            492.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            350.0,
            86.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                2.5
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_blur_1",
              "parameter_shortname": "M Blur",
              "parameter_mmax": 8.0,
              "parameter_mmin": 0.3,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-280",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-281",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            924.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 1 blur"
        }
      },
      {
        "box": {
          "id": "d-282",
          "maxclass": "live.dial",
          "patching_rect": [
            528.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            380.0,
            86.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_radius_scale_1",
              "parameter_shortname": "M Scale",
              "parameter_mmax": 2.0,
              "parameter_mmin": 0.2,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-283",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-284",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            924.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 1 radius_scale"
        }
      },
      {
        "box": {
          "id": "d-285",
          "maxclass": "live.dial",
          "patching_rect": [
            564.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            410.0,
            86.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_segments_1",
              "parameter_shortname": "M Dash",
              "parameter_mmax": 32.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-286",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-287",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            924.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 1 segments"
        }
      },
      {
        "box": {
          "id": "d-288",
          "maxclass": "live.dial",
          "patching_rect": [
            600.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            440.0,
            86.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.4
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_gap_1",
              "parameter_shortname": "M Gap",
              "parameter_mmax": 0.95,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-289",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-290",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            924.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 1 gap"
        }
      },
      {
        "box": {
          "id": "lc-291",
          "maxclass": "live.comment",
          "patching_rect": [
            360.0,
            860.0,
            50.0,
            14.0
          ],
          "text": "Inner",
          "presentation": 1,
          "presentation_rect": [
            258.0,
            108.0,
            30.0,
            18.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Inner ring"
        }
      },
      {
        "box": {
          "id": "d-292",
          "maxclass": "live.dial",
          "patching_rect": [
            420.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            290.0,
            108.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.2
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_skew_2",
              "parameter_shortname": "I Skew",
              "parameter_mmax": 0.5,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-293",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-294",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            1004.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 2 skew"
        }
      },
      {
        "box": {
          "id": "d-295",
          "maxclass": "live.dial",
          "patching_rect": [
            456.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            320.0,
            108.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                2.1
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_phase_2",
              "parameter_shortname": "I Phase",
              "parameter_mmax": 3.14159,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-296",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-297",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            1004.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 2 phase"
        }
      },
      {
        "box": {
          "id": "d-298",
          "maxclass": "live.dial",
          "patching_rect": [
            492.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            350.0,
            108.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.2
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_blur_2",
              "parameter_shortname": "I Blur",
              "parameter_mmax": 8.0,
              "parameter_mmin": 0.3,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-299",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-300",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            1004.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 2 blur"
        }
      },
      {
        "box": {
          "id": "d-301",
          "maxclass": "live.dial",
          "patching_rect": [
            528.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            380.0,
            108.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_radius_scale_2",
              "parameter_shortname": "I Scale",
              "parameter_mmax": 2.0,
              "parameter_mmin": 0.2,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-302",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-303",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            1004.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 2 radius_scale"
        }
      },
      {
        "box": {
          "id": "d-304",
          "maxclass": "live.dial",
          "patching_rect": [
            564.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            410.0,
            108.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_segments_2",
              "parameter_shortname": "I Dash",
              "parameter_mmax": 32.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-305",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-306",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            1004.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 2 segments"
        }
      },
      {
        "box": {
          "id": "d-307",
          "maxclass": "live.dial",
          "patching_rect": [
            600.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            440.0,
            108.0,
            28.0,
            18.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.4
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_gap_2",
              "parameter_shortname": "I Gap",
              "parameter_mmax": 0.95,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "n-308",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-309",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            1004.0,
            180.0,
            22.0
          ],
          "text": "prepend knob oval 2 gap"
        }
      },
      {
        "box": {
          "id": "lc-310",
          "maxclass": "live.comment",
          "patching_rect": [
            420.0,
            782.0,
            40.0,
            12.0
          ],
          "text": "Skew",
          "presentation": 1,
          "presentation_rect": [
            290.0,
            55.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-311",
          "maxclass": "live.comment",
          "patching_rect": [
            456.0,
            782.0,
            40.0,
            12.0
          ],
          "text": "Phase",
          "presentation": 1,
          "presentation_rect": [
            320.0,
            55.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-312",
          "maxclass": "live.comment",
          "patching_rect": [
            492.0,
            782.0,
            40.0,
            12.0
          ],
          "text": "Blur",
          "presentation": 1,
          "presentation_rect": [
            350.0,
            55.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-313",
          "maxclass": "live.comment",
          "patching_rect": [
            528.0,
            782.0,
            40.0,
            12.0
          ],
          "text": "Scale",
          "presentation": 1,
          "presentation_rect": [
            380.0,
            55.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-314",
          "maxclass": "live.comment",
          "patching_rect": [
            564.0,
            782.0,
            40.0,
            12.0
          ],
          "text": "Dash",
          "presentation": 1,
          "presentation_rect": [
            410.0,
            55.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-315",
          "maxclass": "live.comment",
          "patching_rect": [
            600.0,
            782.0,
            40.0,
            12.0
          ],
          "text": "Gap",
          "presentation": 1,
          "presentation_rect": [
            440.0,
            55.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "d-316",
          "maxclass": "live.dial",
          "patching_rect": [
            420.0,
            1080.0,
            24.0,
            28.0
          ],
          "presentation": 1,
          "presentation_rect": [
            290.0,
            132.0,
            28.0,
            22.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                25.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_speed",
              "parameter_shortname": "Impulse Spe",
              "parameter_mmax": 80.0,
              "parameter_mmin": 5.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-317",
          "maxclass": "live.comment",
          "patching_rect": [
            420.0,
            1110.0,
            40.0,
            12.0
          ],
          "text": "Impulse Speed",
          "presentation": 1,
          "presentation_rect": [
            290.0,
            154.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Impulse Speed"
        }
      },
      {
        "box": {
          "id": "n-318",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            1140.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-319",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            1170.0,
            180.0,
            22.0
          ],
          "text": "prepend knob physics speed"
        }
      },
      {
        "box": {
          "id": "d-320",
          "maxclass": "live.dial",
          "patching_rect": [
            456.0,
            1080.0,
            24.0,
            28.0
          ],
          "presentation": 1,
          "presentation_rect": [
            320.0,
            132.0,
            28.0,
            22.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.12
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_radial_offset",
              "parameter_shortname": "Jitter",
              "parameter_mmax": 0.6,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-321",
          "maxclass": "live.comment",
          "patching_rect": [
            456.0,
            1110.0,
            40.0,
            12.0
          ],
          "text": "Jitter",
          "presentation": 1,
          "presentation_rect": [
            320.0,
            154.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Jitter"
        }
      },
      {
        "box": {
          "id": "n-322",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            1140.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-323",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            1170.0,
            180.0,
            22.0
          ],
          "text": "prepend knob physics radial_offset"
        }
      },
      {
        "box": {
          "id": "d-324",
          "maxclass": "live.dial",
          "patching_rect": [
            492.0,
            1080.0,
            24.0,
            28.0
          ],
          "presentation": 1,
          "presentation_rect": [
            350.0,
            132.0,
            28.0,
            22.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.35
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_squishiness",
              "parameter_shortname": "Squishiness",
              "parameter_mmax": 1.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-325",
          "maxclass": "live.comment",
          "patching_rect": [
            492.0,
            1110.0,
            40.0,
            12.0
          ],
          "text": "Squishiness",
          "presentation": 1,
          "presentation_rect": [
            350.0,
            154.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Squishiness"
        }
      },
      {
        "box": {
          "id": "n-326",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            1140.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-327",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            1170.0,
            180.0,
            22.0
          ],
          "text": "prepend knob physics squishiness"
        }
      },
      {
        "box": {
          "id": "d-328",
          "maxclass": "live.dial",
          "patching_rect": [
            528.0,
            1080.0,
            24.0,
            28.0
          ],
          "presentation": 1,
          "presentation_rect": [
            380.0,
            132.0,
            28.0,
            22.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.3
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_damping",
              "parameter_shortname": "Viscosity",
              "parameter_mmax": 5.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-329",
          "maxclass": "live.comment",
          "patching_rect": [
            528.0,
            1110.0,
            40.0,
            12.0
          ],
          "text": "Viscosity",
          "presentation": 1,
          "presentation_rect": [
            380.0,
            154.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Viscosity"
        }
      },
      {
        "box": {
          "id": "n-330",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            1140.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-331",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            1170.0,
            180.0,
            22.0
          ],
          "text": "prepend knob physics damping"
        }
      },
      {
        "box": {
          "id": "d-332",
          "maxclass": "live.dial",
          "patching_rect": [
            564.0,
            1080.0,
            24.0,
            28.0
          ],
          "presentation": 1,
          "presentation_rect": [
            410.0,
            132.0,
            28.0,
            22.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.75
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_bounce",
              "parameter_shortname": "Bounce",
              "parameter_mmax": 1.0,
              "parameter_mmin": 0.1,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-333",
          "maxclass": "live.comment",
          "patching_rect": [
            564.0,
            1110.0,
            40.0,
            12.0
          ],
          "text": "Bounce",
          "presentation": 1,
          "presentation_rect": [
            410.0,
            154.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Bounce"
        }
      },
      {
        "box": {
          "id": "n-334",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            1140.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-335",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            1170.0,
            180.0,
            22.0
          ],
          "text": "prepend knob physics bounce"
        }
      },
      {
        "box": {
          "id": "d-336",
          "maxclass": "live.dial",
          "patching_rect": [
            600.0,
            1080.0,
            24.0,
            28.0
          ],
          "presentation": 1,
          "presentation_rect": [
            440.0,
            132.0,
            28.0,
            22.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                3.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_center_pull",
              "parameter_shortname": "Center Pull",
              "parameter_mmax": 15.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-337",
          "maxclass": "live.comment",
          "patching_rect": [
            600.0,
            1110.0,
            40.0,
            12.0
          ],
          "text": "Center Pull",
          "presentation": 1,
          "presentation_rect": [
            440.0,
            154.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Center Pull"
        }
      },
      {
        "box": {
          "id": "n-338",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            1140.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-339",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            1170.0,
            180.0,
            22.0
          ],
          "text": "prepend knob physics center_pull"
        }
      },
      {
        "box": {
          "id": "d-340",
          "maxclass": "live.dial",
          "patching_rect": [
            636.0,
            1080.0,
            24.0,
            28.0
          ],
          "presentation": 1,
          "presentation_rect": [
            470.0,
            132.0,
            28.0,
            22.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.25
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_tau_squash",
              "parameter_shortname": "Squash \u03c4",
              "parameter_mmax": 1.0,
              "parameter_mmin": 0.05,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-341",
          "maxclass": "live.comment",
          "patching_rect": [
            636.0,
            1110.0,
            40.0,
            12.0
          ],
          "text": "Squash \u03c4",
          "presentation": 1,
          "presentation_rect": [
            470.0,
            154.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Squash \u03c4"
        }
      },
      {
        "box": {
          "id": "n-342",
          "maxclass": "newobj",
          "patching_rect": [
            636.0,
            1140.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-343",
          "maxclass": "newobj",
          "patching_rect": [
            636.0,
            1170.0,
            180.0,
            22.0
          ],
          "text": "prepend knob physics tau_squash"
        }
      },
      {
        "box": {
          "id": "d-344",
          "maxclass": "live.dial",
          "patching_rect": [
            672.0,
            1080.0,
            24.0,
            28.0
          ],
          "presentation": 1,
          "presentation_rect": [
            500.0,
            132.0,
            28.0,
            22.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                40.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_max_velocity",
              "parameter_shortname": "Max Velocit",
              "parameter_mmax": 120.0,
              "parameter_mmin": 10.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-345",
          "maxclass": "live.comment",
          "patching_rect": [
            672.0,
            1110.0,
            40.0,
            12.0
          ],
          "text": "Max Velocity",
          "presentation": 1,
          "presentation_rect": [
            500.0,
            154.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Max Velocity"
        }
      },
      {
        "box": {
          "id": "n-346",
          "maxclass": "newobj",
          "patching_rect": [
            672.0,
            1140.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-347",
          "maxclass": "newobj",
          "patching_rect": [
            672.0,
            1170.0,
            180.0,
            22.0
          ],
          "text": "prepend knob physics max_velocity"
        }
      },
      {
        "box": {
          "id": "d-348",
          "maxclass": "live.dial",
          "patching_rect": [
            708.0,
            1080.0,
            24.0,
            28.0
          ],
          "presentation": 1,
          "presentation_rect": [
            530.0,
            132.0,
            28.0,
            22.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.6
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_angular_friction",
              "parameter_shortname": "Rot Frictio",
              "parameter_mmax": 4.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-349",
          "maxclass": "live.comment",
          "patching_rect": [
            708.0,
            1110.0,
            40.0,
            12.0
          ],
          "text": "Rot Friction",
          "presentation": 1,
          "presentation_rect": [
            530.0,
            154.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Rot Friction"
        }
      },
      {
        "box": {
          "id": "n-350",
          "maxclass": "newobj",
          "patching_rect": [
            708.0,
            1140.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-351",
          "maxclass": "newobj",
          "patching_rect": [
            708.0,
            1170.0,
            180.0,
            22.0
          ],
          "text": "prepend knob physics angular_friction"
        }
      },
      {
        "box": {
          "id": "d-352",
          "maxclass": "live.dial",
          "patching_rect": [
            744.0,
            1080.0,
            24.0,
            28.0
          ],
          "presentation": 1,
          "presentation_rect": [
            560.0,
            132.0,
            28.0,
            22.0
          ],
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.35
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_squash_damping",
              "parameter_shortname": "Squash \u03b6",
              "parameter_mmax": 1.5,
              "parameter_mmin": 0.05,
              "parameter_type": 0,
              "parameter_unitstyle": 0,
              "parameter_exponent": 1.0
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-353",
          "maxclass": "live.comment",
          "patching_rect": [
            744.0,
            1110.0,
            40.0,
            12.0
          ],
          "text": "Squash \u03b6",
          "presentation": 1,
          "presentation_rect": [
            560.0,
            154.0,
            32.0,
            9.0
          ],
          "fontsize": 7.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Squash \u03b6"
        }
      },
      {
        "box": {
          "id": "n-354",
          "maxclass": "newobj",
          "patching_rect": [
            744.0,
            1140.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-355",
          "maxclass": "newobj",
          "patching_rect": [
            744.0,
            1170.0,
            180.0,
            22.0
          ],
          "text": "prepend knob physics squash_damping"
        }
      },
      {
        "box": {
          "id": "lc-356",
          "maxclass": "live.comment",
          "patching_rect": [
            760.0,
            40.0,
            60.0,
            14.0
          ],
          "text": "host",
          "presentation": 1,
          "presentation_rect": [
            780.0,
            24.0,
            36.0,
            12.0
          ],
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "te-357",
          "maxclass": "textedit",
          "patching_rect": [
            760.0,
            70.0,
            120.0,
            22.0
          ],
          "text": "here.local",
          "presentation": 1,
          "presentation_rect": [
            810.0,
            24.0,
            100.0,
            14.0
          ],
          "keymode": 1,
          "numinlets": 1,
          "numoutlets": 4,
          "outlettype": [
            "",
            "int",
            "",
            ""
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                "here.local"
              ],
              "parameter_initial_enable": 1,
              "parameter_invisible": 1,
              "parameter_longname": "here_host",
              "parameter_shortname": "here_host",
              "parameter_type": 3
            }
          }
        }
      },
      {
        "box": {
          "id": "n-358",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            100.0,
            100.0,
            22.0
          ],
          "text": "route text"
        }
      },
      {
        "box": {
          "id": "n-359",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            130.0,
            100.0,
            22.0
          ],
          "text": "prepend host"
        }
      },
      {
        "box": {
          "id": "lc-360",
          "maxclass": "live.comment",
          "patching_rect": [
            760.0,
            160.0,
            60.0,
            14.0
          ],
          "text": "port",
          "presentation": 1,
          "presentation_rect": [
            780.0,
            42.0,
            36.0,
            12.0
          ],
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "te-361",
          "maxclass": "textedit",
          "patching_rect": [
            760.0,
            190.0,
            120.0,
            22.0
          ],
          "text": "9000",
          "presentation": 1,
          "presentation_rect": [
            810.0,
            42.0,
            60.0,
            14.0
          ],
          "keymode": 1,
          "numinlets": 1,
          "numoutlets": 4,
          "outlettype": [
            "",
            "int",
            "",
            ""
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                9000
              ],
              "parameter_initial_enable": 1,
              "parameter_invisible": 1,
              "parameter_longname": "here_port",
              "parameter_shortname": "here_port",
              "parameter_type": 3
            }
          }
        }
      },
      {
        "box": {
          "id": "n-362",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            220.0,
            100.0,
            22.0
          ],
          "text": "route text"
        }
      },
      {
        "box": {
          "id": "n-363",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            250.0,
            100.0,
            22.0
          ],
          "text": "prepend port"
        }
      },
      {
        "box": {
          "id": "b-364",
          "maxclass": "live.button",
          "patching_rect": [
            760.0,
            290.0,
            24.0,
            24.0
          ],
          "presentation": 1,
          "presentation_rect": [
            780.0,
            64.0,
            22.0,
            14.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "here_test",
              "parameter_shortname": "test",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "n-365",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "palette 0"
        }
      },
      {
        "box": {
          "id": "lc-366",
          "maxclass": "live.comment",
          "patching_rect": [
            790.0,
            290.0,
            60.0,
            14.0
          ],
          "text": "test ping",
          "presentation": 1,
          "presentation_rect": [
            806.0,
            64.0,
            60.0,
            12.0
          ],
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "tog-367",
          "maxclass": "live.toggle",
          "patching_rect": [
            760.0,
            350.0,
            24.0,
            24.0
          ],
          "presentation": 1,
          "presentation_rect": [
            780.0,
            82.0,
            16.0,
            16.0
          ],
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_debug",
              "parameter_shortname": "debug",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "n-368",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            380.0,
            80.0,
            22.0
          ],
          "text": "gate 1 0"
        }
      },
      {
        "box": {
          "id": "n-369",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            410.0,
            80.0,
            22.0
          ],
          "text": "print HERE"
        }
      },
      {
        "box": {
          "id": "lc-370",
          "maxclass": "live.comment",
          "patching_rect": [
            790.0,
            350.0,
            60.0,
            14.0
          ],
          "text": "debug",
          "presentation": 1,
          "presentation_rect": [
            800.0,
            82.0,
            60.0,
            12.0
          ],
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-371",
          "maxclass": "live.comment",
          "patching_rect": [
            760.0,
            450.0,
            200.0,
            14.0
          ],
          "text": "Plays MIDI clips \u2192 OSC \u2192 here.local",
          "presentation": 1,
          "presentation_rect": [
            780.0,
            102.0,
            130.0,
            12.0
          ],
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "n-372",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            4.0,
            80.0,
            22.0
          ],
          "text": "live.thisdevice",
          "numinlets": 1,
          "numoutlets": 3
        }
      },
      {
        "box": {
          "id": "n-373",
          "maxclass": "newobj",
          "patching_rect": [
            110.0,
            4.0,
            60.0,
            22.0
          ],
          "text": "reset"
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "destination": [
            "n-3",
            0
          ],
          "source": [
            "n-2",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-4",
            0
          ],
          "source": [
            "n-2",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-6",
            0
          ],
          "source": [
            "n-3",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-6",
            1
          ],
          "source": [
            "n-3",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-7",
            0
          ],
          "source": [
            "n-6",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-7",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-8",
            0
          ],
          "source": [
            "n-5",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-11",
            0
          ],
          "source": [
            "t-9",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-12",
            0
          ],
          "source": [
            "n-11",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-12",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-13",
            0
          ],
          "source": [
            "n-11",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-13",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-16",
            0
          ],
          "source": [
            "t-14",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-17",
            0
          ],
          "source": [
            "n-16",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-17",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-18",
            0
          ],
          "source": [
            "n-16",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-18",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-21",
            0
          ],
          "source": [
            "t-19",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-22",
            0
          ],
          "source": [
            "n-21",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-22",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-23",
            0
          ],
          "source": [
            "n-21",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-23",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-26",
            0
          ],
          "source": [
            "t-24",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-27",
            0
          ],
          "source": [
            "n-26",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-27",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-28",
            0
          ],
          "source": [
            "n-26",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-28",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-31",
            0
          ],
          "source": [
            "t-29",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-32",
            0
          ],
          "source": [
            "n-31",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-32",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-33",
            0
          ],
          "source": [
            "n-31",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-33",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-36",
            0
          ],
          "source": [
            "t-34",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-37",
            0
          ],
          "source": [
            "n-36",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-37",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-38",
            0
          ],
          "source": [
            "n-36",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-38",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-41",
            0
          ],
          "source": [
            "t-39",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-42",
            0
          ],
          "source": [
            "n-41",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-42",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-43",
            0
          ],
          "source": [
            "n-41",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-43",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-46",
            0
          ],
          "source": [
            "t-44",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-47",
            0
          ],
          "source": [
            "n-46",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-47",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-48",
            0
          ],
          "source": [
            "n-46",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-48",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-51",
            0
          ],
          "source": [
            "t-49",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-52",
            0
          ],
          "source": [
            "n-51",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-52",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-53",
            0
          ],
          "source": [
            "n-51",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-53",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-56",
            0
          ],
          "source": [
            "t-54",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-57",
            0
          ],
          "source": [
            "n-56",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-57",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-58",
            0
          ],
          "source": [
            "n-56",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-58",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-61",
            0
          ],
          "source": [
            "t-59",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-62",
            0
          ],
          "source": [
            "n-61",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-62",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-63",
            0
          ],
          "source": [
            "n-61",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-63",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-66",
            0
          ],
          "source": [
            "t-64",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-67",
            0
          ],
          "source": [
            "n-66",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-67",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-68",
            0
          ],
          "source": [
            "n-66",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-68",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-71",
            0
          ],
          "source": [
            "t-69",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-72",
            0
          ],
          "source": [
            "n-71",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-72",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-73",
            0
          ],
          "source": [
            "n-71",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-73",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-76",
            0
          ],
          "source": [
            "t-74",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-77",
            0
          ],
          "source": [
            "n-76",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-77",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-78",
            0
          ],
          "source": [
            "n-76",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-78",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-81",
            0
          ],
          "source": [
            "t-79",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-82",
            0
          ],
          "source": [
            "n-81",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-82",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-83",
            0
          ],
          "source": [
            "n-81",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-83",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-86",
            0
          ],
          "source": [
            "t-84",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-87",
            0
          ],
          "source": [
            "n-86",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-87",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-88",
            0
          ],
          "source": [
            "n-86",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-88",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-91",
            0
          ],
          "source": [
            "t-89",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-92",
            0
          ],
          "source": [
            "n-91",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-92",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-93",
            0
          ],
          "source": [
            "n-91",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-93",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-96",
            0
          ],
          "source": [
            "t-94",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-97",
            0
          ],
          "source": [
            "n-96",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-97",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-98",
            0
          ],
          "source": [
            "n-96",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-98",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-101",
            0
          ],
          "source": [
            "t-99",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-102",
            0
          ],
          "source": [
            "n-101",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-102",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-103",
            0
          ],
          "source": [
            "n-101",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-103",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-106",
            0
          ],
          "source": [
            "t-104",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-107",
            0
          ],
          "source": [
            "n-106",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-107",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-108",
            0
          ],
          "source": [
            "n-106",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-108",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-111",
            0
          ],
          "source": [
            "t-109",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-112",
            0
          ],
          "source": [
            "n-111",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-112",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-113",
            0
          ],
          "source": [
            "n-111",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-113",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-116",
            0
          ],
          "source": [
            "t-114",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-117",
            0
          ],
          "source": [
            "n-116",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-117",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-118",
            0
          ],
          "source": [
            "n-116",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-118",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-121",
            0
          ],
          "source": [
            "t-119",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-122",
            0
          ],
          "source": [
            "n-121",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-122",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-123",
            0
          ],
          "source": [
            "n-121",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-123",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-126",
            0
          ],
          "source": [
            "t-124",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-127",
            0
          ],
          "source": [
            "n-126",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-127",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-128",
            0
          ],
          "source": [
            "n-126",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-128",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-131",
            0
          ],
          "source": [
            "t-129",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-132",
            0
          ],
          "source": [
            "n-131",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-132",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-133",
            0
          ],
          "source": [
            "n-131",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-133",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-136",
            0
          ],
          "source": [
            "t-134",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-137",
            0
          ],
          "source": [
            "n-136",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-137",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-138",
            0
          ],
          "source": [
            "n-136",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-138",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-141",
            0
          ],
          "source": [
            "t-139",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-142",
            0
          ],
          "source": [
            "n-141",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-142",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-143",
            0
          ],
          "source": [
            "n-141",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-143",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-146",
            0
          ],
          "source": [
            "t-144",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-147",
            0
          ],
          "source": [
            "n-146",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-147",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-148",
            0
          ],
          "source": [
            "n-146",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-148",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-151",
            0
          ],
          "source": [
            "t-149",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-152",
            0
          ],
          "source": [
            "n-151",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-152",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-153",
            0
          ],
          "source": [
            "n-151",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-153",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-156",
            0
          ],
          "source": [
            "t-154",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-157",
            0
          ],
          "source": [
            "n-156",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-157",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-158",
            0
          ],
          "source": [
            "n-156",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-158",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-161",
            0
          ],
          "source": [
            "t-159",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-162",
            0
          ],
          "source": [
            "n-161",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-162",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-163",
            0
          ],
          "source": [
            "n-161",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-163",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-166",
            0
          ],
          "source": [
            "t-164",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-167",
            0
          ],
          "source": [
            "n-166",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-167",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-168",
            0
          ],
          "source": [
            "n-166",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-168",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-171",
            0
          ],
          "source": [
            "t-169",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-172",
            0
          ],
          "source": [
            "n-171",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-172",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-173",
            0
          ],
          "source": [
            "n-171",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-173",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-176",
            0
          ],
          "source": [
            "t-174",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-177",
            0
          ],
          "source": [
            "n-176",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-177",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-178",
            0
          ],
          "source": [
            "n-176",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-178",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-181",
            0
          ],
          "source": [
            "t-179",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-182",
            0
          ],
          "source": [
            "n-181",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-182",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-183",
            0
          ],
          "source": [
            "n-181",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-183",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-186",
            0
          ],
          "source": [
            "t-184",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-187",
            0
          ],
          "source": [
            "n-186",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-187",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-188",
            0
          ],
          "source": [
            "n-186",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-188",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-191",
            0
          ],
          "source": [
            "t-189",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-192",
            0
          ],
          "source": [
            "n-191",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-192",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-193",
            0
          ],
          "source": [
            "n-191",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-193",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-196",
            0
          ],
          "source": [
            "t-194",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-197",
            0
          ],
          "source": [
            "n-196",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-197",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-198",
            0
          ],
          "source": [
            "n-196",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-198",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-201",
            0
          ],
          "source": [
            "t-199",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-202",
            0
          ],
          "source": [
            "n-201",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-202",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-203",
            0
          ],
          "source": [
            "n-201",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-203",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-206",
            0
          ],
          "source": [
            "t-204",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-207",
            0
          ],
          "source": [
            "n-206",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-207",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-208",
            0
          ],
          "source": [
            "n-206",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-208",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-211",
            0
          ],
          "source": [
            "d-209",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-212",
            0
          ],
          "source": [
            "n-211",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-212",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-215",
            0
          ],
          "source": [
            "d-213",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-216",
            0
          ],
          "source": [
            "n-215",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-216",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-219",
            0
          ],
          "source": [
            "d-217",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-220",
            0
          ],
          "source": [
            "n-219",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-220",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-223",
            0
          ],
          "source": [
            "d-221",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-224",
            0
          ],
          "source": [
            "n-223",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-224",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-227",
            0
          ],
          "source": [
            "d-225",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-228",
            0
          ],
          "source": [
            "n-227",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-228",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-231",
            0
          ],
          "source": [
            "d-229",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-232",
            0
          ],
          "source": [
            "n-231",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-232",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-235",
            0
          ],
          "source": [
            "d-233",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-236",
            0
          ],
          "source": [
            "n-235",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-236",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-239",
            0
          ],
          "source": [
            "d-237",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-240",
            0
          ],
          "source": [
            "n-239",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-240",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-243",
            0
          ],
          "source": [
            "d-241",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-244",
            0
          ],
          "source": [
            "n-243",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-244",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-247",
            0
          ],
          "source": [
            "d-245",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-248",
            0
          ],
          "source": [
            "n-247",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-248",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-251",
            0
          ],
          "source": [
            "d-249",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-252",
            0
          ],
          "source": [
            "n-251",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-252",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-255",
            0
          ],
          "source": [
            "d-254",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-256",
            0
          ],
          "source": [
            "n-255",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-256",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-258",
            0
          ],
          "source": [
            "d-257",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-259",
            0
          ],
          "source": [
            "n-258",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-259",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-261",
            0
          ],
          "source": [
            "d-260",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-262",
            0
          ],
          "source": [
            "n-261",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-262",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-264",
            0
          ],
          "source": [
            "d-263",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-265",
            0
          ],
          "source": [
            "n-264",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-265",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-267",
            0
          ],
          "source": [
            "d-266",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-268",
            0
          ],
          "source": [
            "n-267",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-268",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-270",
            0
          ],
          "source": [
            "d-269",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-271",
            0
          ],
          "source": [
            "n-270",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-271",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-274",
            0
          ],
          "source": [
            "d-273",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-275",
            0
          ],
          "source": [
            "n-274",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-275",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-277",
            0
          ],
          "source": [
            "d-276",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-278",
            0
          ],
          "source": [
            "n-277",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-278",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-280",
            0
          ],
          "source": [
            "d-279",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-281",
            0
          ],
          "source": [
            "n-280",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-281",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-283",
            0
          ],
          "source": [
            "d-282",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-284",
            0
          ],
          "source": [
            "n-283",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-284",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-286",
            0
          ],
          "source": [
            "d-285",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-287",
            0
          ],
          "source": [
            "n-286",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-287",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-289",
            0
          ],
          "source": [
            "d-288",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-290",
            0
          ],
          "source": [
            "n-289",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-290",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-293",
            0
          ],
          "source": [
            "d-292",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-294",
            0
          ],
          "source": [
            "n-293",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-294",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-296",
            0
          ],
          "source": [
            "d-295",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-297",
            0
          ],
          "source": [
            "n-296",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-297",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-299",
            0
          ],
          "source": [
            "d-298",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-300",
            0
          ],
          "source": [
            "n-299",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-300",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-302",
            0
          ],
          "source": [
            "d-301",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-303",
            0
          ],
          "source": [
            "n-302",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-303",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-305",
            0
          ],
          "source": [
            "d-304",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-306",
            0
          ],
          "source": [
            "n-305",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-306",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-308",
            0
          ],
          "source": [
            "d-307",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-309",
            0
          ],
          "source": [
            "n-308",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-309",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-318",
            0
          ],
          "source": [
            "d-316",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-319",
            0
          ],
          "source": [
            "n-318",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-319",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-322",
            0
          ],
          "source": [
            "d-320",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-323",
            0
          ],
          "source": [
            "n-322",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-323",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-326",
            0
          ],
          "source": [
            "d-324",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-327",
            0
          ],
          "source": [
            "n-326",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-327",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-330",
            0
          ],
          "source": [
            "d-328",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-331",
            0
          ],
          "source": [
            "n-330",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-331",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-334",
            0
          ],
          "source": [
            "d-332",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-335",
            0
          ],
          "source": [
            "n-334",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-335",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-338",
            0
          ],
          "source": [
            "d-336",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-339",
            0
          ],
          "source": [
            "n-338",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-339",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-342",
            0
          ],
          "source": [
            "d-340",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-343",
            0
          ],
          "source": [
            "n-342",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-343",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-346",
            0
          ],
          "source": [
            "d-344",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-347",
            0
          ],
          "source": [
            "n-346",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-347",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-350",
            0
          ],
          "source": [
            "d-348",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-351",
            0
          ],
          "source": [
            "n-350",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-351",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-354",
            0
          ],
          "source": [
            "d-352",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-355",
            0
          ],
          "source": [
            "n-354",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-355",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-358",
            0
          ],
          "source": [
            "te-357",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-359",
            0
          ],
          "source": [
            "n-358",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-8",
            0
          ],
          "source": [
            "n-359",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-362",
            0
          ],
          "source": [
            "te-361",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-363",
            0
          ],
          "source": [
            "n-362",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-8",
            0
          ],
          "source": [
            "n-363",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-365",
            0
          ],
          "source": [
            "b-364",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-365",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-368",
            0
          ],
          "source": [
            "tog-367",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-368",
            1
          ],
          "source": [
            "n-5",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-369",
            0
          ],
          "source": [
            "n-368",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-373",
            0
          ],
          "source": [
            "n-372",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-373",
            0
          ]
        }
      }
    ]
  }
}
