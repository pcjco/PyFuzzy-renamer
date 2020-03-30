This application uses a list of input strings and will rename each one with the most similar string from another list of strings.

### Terminology

The following terminology is used in the application, and in this document:

*   The input strings to rename are called the **sources**;
*   The strings used to search for similarity are called the **choices**;
*   The process to search the most similar **choice** for a given **source** is referred here as **matching** process;
*   When strings are coming from file paths, the following terminology is used:
    *   A **file path** is composed of a **parent directory** and a **file name**;

        e.g. **file path**=`c:/foo/bar/setup.tar.gz`, **parent directory**=`c:/foo/bar`, **file name**=`setup.tar.gz`
    *   A **file name** is composed of a **stem** and a **suffix**;

        e.g. **file name**=`setup.tar.gz`, **stem**=`setup.tar`, **suffix**=`.gz`
    * A **suffix** can only contain alphanumeric characters after the dot, if it contains non-alphanumeric characters, the **suffix** is considered as part of the **stem**

        e.g. **file name**=`A.Train III`, **stem**=`A.Train III`, **suffix**=`None`


### Principles

Here is the process applied to match and rename each **source**:

<pre>
 Choices────┐
            │
        ┌───┴────┐                     ┌────────┐
 Source─┤Matching├─Most Similar Choice─┤Renaming├─Renamed Source
        └────────┘                     └────────┘
</pre>

When searching for the most similar **choice**, only the **stems** of **choices** and **stem** of **source** are compared.

When renaming a **source** file path, only the **stem** is renamed with the most similar **stem** among **choices** file paths.

E.g. if **source** is `c:/foo/Amaryllis.png`, and **most similar choice** is `d:/bar/Amaryllidinae.jpg`, **renamed source** is `c:/foo/Amaryllidinae.png`

If **masks** and **filters** are applied, the process applied to match and rename each **source** is the following:

<pre>
                                ┌─────────┐
                      Choices───┤Filtering├────Filtered Choices────────┐
                                └─────────┘                            │
        ┌───────┐               ┌─────────┐                        ┌───┴────┐                     ┌────────┐                       ┌─────────┐
 Source─┤Masking├─Masked Source─┤Filtering├─Masked&Filtered Source─┤Matching├─Most Similar Choice─┤Renaming├─Masked Renamed Source─┤Unmasking├─Unmasked Renamed Source
        └───┬───┘               └─────────┘                        └────────┘                     └────────┘                       └────┬────┘
            │                                                                                                                           │
            └────────────────────────────────────────── Leading & Trailing Masks ───────────────────────────────────────────────────────┘
</pre>

### Sources

Sources are entered in the following ways:

*   click on the **`Sources`** button to add a selection of file paths to the current **sources**;
*   Go to **`File->Sources->Sources from Directory`** menu to add file paths from a selected folder to the current **sources**;
*   Go to **`File->Sources->Sources from Clipboard`** menu to add file paths from clipboard to the current **sources**. If clipboard contains a folder, then the file paths of the files inside this folder are added;
*   Drag files or folders into application panel and choose **`Sources`** to add file paths to the current **sources**. For folders, the file paths of the files inside folders are added;
*   Paste (Ctrl+V) into application panel and choose **`Sources`** to add file paths or folders in clipboard to the current **sources**. For folders, the file paths of the files inside folders are added

### Choices

Choices are entered in the following ways:

*   click on the **`Choices`** button to add a selection of file paths to the current **choices**;
*   Go to **`File->Choices->Choices from Directory`** menu to add file paths from a selected folder to the current **choices**;
*   Go to **`File->Choices->Choices from Clipboard`** menu to add files paths from clipboard to the current **choices**. If clipboard contains a folder, then the file paths of the files inside this folder are added;
*   Drag files or folders into application panel and choose **`Choices`** to add file paths to the current **choices**. For folders, the file paths of the files inside folders are added;
*   Paste (Ctrl+V) into application panel and choose **`Choices`** to add file paths or folders in clipboard to the current **choices**. For folders, the file paths of the files inside folders are added

### Filters

To ease the **matching** process, filters can be applied to **sources** and **choices** before they are compared.

E.g. **source** is `c:/foo/The Amaryllis.png` and **choice** is `d:/bar/Amaryllidinae, The.txt`. It would be smart to clean the **sources** and **choices** by ignoring all articles before trying to find the **most similar choice**.

To achieve this, the application uses **filters**.

The filters are using Python regular expression patterns with capture groups (). The captured groups are replaced by a given expression (usually empty to clean a string). This is applied to both **sources** and **choices** when **matching** occurs.

Filters are only applied for the **matching** process, original unfiltered files are used otherwise.

For example, to clean articles of **source** and **choice** file, a filter with the pattern `(^the\b|, the)` with an empty replacement ` ` could be used:

1.  **Filtering source**: `c:/foo/The Amaryllis.png` ⭢ `Amaryllis`
2.  **Filtering choice**: `d:/bar/Amaryllidinae, The.txt` ⭢ `Amaryllidinae`
3.  **Matching**: `The Amaryllis` ⭢ `Amaryllidinae, The`
4.  **Renaming**: `c:/foo/The Amaryllis.png` ⭢ `c:/foo/Amaryllidinae, The.png`

Filters creation, addition, deletion, re-ordering is available from **`Masks & Filters`** button.

*   Edition of the filter name, pattern and replace is done directly by clicking on the filter list cells
*   Deletion of filters is done by pressing the [DELETE] key on some selected filter items or from the context menu on selected filter items.
*   Addition of a filter is done from the context menu on filter list.
*   Re-ordering a filter is done by dragging and dropping the filter item across the filter list.

### Masks

Sometimes, it can be interesting to ignore some leading and/or trailing parts from a **source** in the **matching** process and restore them after the **renaming** process. It is particularly important in order to enhance **matching** when **choices** don't contain these parts.

E.g. **source** is `c:/foo/(1983-06-22) Amaryllis [Russia].png`, and we want to ignore the date `(1983-06-22)` and the country `[Russia]` during **matching** but we need to restore them when **renaming**, then if **most similar choice** is `d:/bar/Amaryllidinae.jpg`, the **renamed source** should be `c:/foo/(1983-06-22) Amaryllidinae [Russia].png`

To achieve this, the application uses **masks**.

The masks are using Python regular expression patterns. They are removed from **sources** strings before **filtering** and **matching** occur. It is used to remove leading and trailing expressions (year, disk#...) before **matching** and restore them after **renaming**.

For example, to preserve the Disk number at the end of a **source** file, a mask with the pattern `(\s?disk\d)$` could be used:

1.  **Masking**: `c:/foo/The Wiiire Disk1.rom` ⭢ `The Wiiire` + Trailing mask = `Disk1`
2.  **Matching**: `The Wiiire` ⭢ `The Wire`
3.  **Renaming**: `c:/foo/The Wiiire.rom` ⭢ `c:/foo/The Wire.rom`
4.  **Unmkasking**: `c:/foo/The Wiiire.rom` ⭢ `c:/foo/The Wire Disk1.rom`

Masks creation, addition, deletion, re-ordering is available from **`Masks & Filters`** button.

*   Edition of the mask name and pattern is done directly by clicking on the mask list cells
*   Deletion of masks is done by pressing the [DELETE] key on some selected mask items or from the context menu on selected mask items.
*   Addition of a mask is done from the context menu on mask list.
*   Re-ordering a mask is done by dragging and dropping the mask item across the mask list.

### Output directory

When **source** strings are coming from file paths, the **renaming** process will modify the file paths.
There are two options available:
 1. Renaming in place : the **source** file is renamed to the **most similar choice** in the same directory
 
    This is done by selecting **`Output Directory->Same as input`**
 2. Renaming in another directory : the **source** file is kept and the renamed file is copied in another directory

    This is done by selecting **`Output Directory->User-defined directory`**

### Options

*   **View full path**

    When **source** strings are coming from file paths, the full path of files are shown in the **`Source Name`** and **`Renaming Preview`** columns.  
    When **choices** strings are coming from file paths, the full path of files are shown in the **`Closest Match`** columns.

*   **Hide suffix**

    When **source** strings are coming from file paths, the suffixes are hidden in the **`Source Name`** and **`Renaming Preview`** columns.  
    When **choices** strings are coming from file paths, the suffixes are hidden in the **`Closest Match`** columns.

*   **Keep matched file suffix**

    During **renaming**, the suffix of the **most similar choice** is used before suffix of the **source**.  
    E.g. if **source** is `Amaryllis.png`, and **most similar choice** is `Amaryllidinae.rom`, **renamed source** is `Amaryllidinae.rom.png`

*   **Always match first letter**
    
    During **matching**, each **source** will search for the **most similar choice** among **choices** that start with the same letter only.
