# HC2EM Inventory

## Purpose

`get_inventory` helps Harvard Cryo-EM Center staff search the grid inventory directories and produce a report for selected dates. At HC2EM, the inventories are created and sorted by user, but oftentimes staff members need to find/sort them by dates, such as checking what to clip/unload/load for today, or figuring out what happened on March 10th 2020.

## Requirements

- macOS/unix
- Python 3
- Dropbox desktop app installed and access to the shared Harvard Cryo-EM Center Dropbox content
- The user submitted the correct inventory file in .pdf format, with the filename containing the session date

The expected search location is below, but if it does not exist, the script will search for it

```text
~/Dropbox/Harvard Cryo-EM Center/Grid_inventory_and_data_collection_sheets/User_Directories
```

## Install

Clone the repository and enter its folder, or maybe just copy this short script to your preferred work directory.

```bash
git clone https://github.com/QiuyeLi/hc2em_inventory
cd hc2em_inventory
```

## Run

From the repository folder, run:

```bash
python get_inventory.py
```

When prompted:

- Enter a date as `YYYYMMDD`, or press Enter to use today.
- Enter the requested lookback value to include the desired prior period. This can be helpful if you only know the unload date, or are trying to find the inventory for unloading
- Use `c` to copy, `q` to quit, or `s` to select when those options are offered by the script.

Reports are written to:

```text
<repo>/output/YYYY_Mon_DD
```

## Reviewing results

The script uses filename and directory matching to build an overview. Manually review the output and any ambiguous, missing, or unexpected matches before relying on the report.

Terminal messages may use color to make status and review items easier to identify. To disable colored output, run:

```bash
NO_COLOR=1 python get_inventory.py
```

## Dropbox cloud-only files

If Dropbox files or folders are cloud-only, they may need to be downloaded locally before the script can inspect them. The script will try to read the files before copying, so file downloading can be triggered. 

## Future plan

Potential future companion script:

    set_inventory.py

This could send staff-updated inventory PDFs back to the appropriate user
folders. 

## Author

Qiuye Li
