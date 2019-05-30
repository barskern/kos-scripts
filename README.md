# kos-scripts

My scripts (and supporting tools) for the Kerbal Space Program mod kOS (Kerbal Operating System).

- [Kerbal Space Program on Steam](https://store.steampowered.com/app/220200/Kerbal_Space_Program/)
- [kOS Documentation](https://ksp-kos.github.io/KOS/)

Many ideas and implementation decisions taken from the excellent [Kerbal Space Programming][kerbal-space-programming] series.

## Structure

All of the kOS code (KerboScript) is contained under the `source` folder. Within this folder there are a few subdirectories, outlined below.

- *boot* - All of my bootloaders which will be executed whenever a kOSProcessor starts up. See [Bootloaders](#bootloaders).
- *leolib* - My personal library of KerboScript functions. Meant to be re-used across actions and missions.
- *actions* - One-off activities that are meant to be generic across vessels and generally too complex to be contained in a library.
- *missions* - Typically a composition of 'actions' as well as glue logic to piece them together. Can also be arbitrary KerboScript to run.

## Bootloaders

There are three types of bootloaders supported.
- *shell* - The simplest bootloader, just executes `lib_bootstrap` and opens the terminal window. 
- *beacon* - A fairly lightweight bootloader that bootstraps and then waits for update files to be pushed from mission control. Very much inspired by [Kerbal Space Programming][kerbal-space-programming].
  - This is my most commonly used bootloader
- *gui* - A pretty heavy bootloader that opens up a custom graphical user interface (GUI). The intent is for this UI to be able to guess what you would want to do at any given time and only show the relevant options, allowing for configuration when necessary.
  - This is not quite mission ready.
  - This is heavy, and I recommend only using it on vessels with large disk sizes.

## Actions vs. Missions

My primary workflow for controlling vessels through kOS is as follows:

1. Set vessel to use `beacon` bootloader
2. (optional) Develop a mission script for the task I am trying to accomplish
  - This really depends on the level of complexity or strictness of the timing requirements for what I am trying to do.
3. Use `make push-action ...` and `make push-mission ...` to transfer actions/missions to the vessel. Wash, rinse, repeat.
4. Do a post-mortem to decide which `actions` would be most useful in the future to more easily glue together full missions

### Action Example

An action `blinky` can be pushed to the vessel named `kostest` with the following command on the host machine (i.e. not in a kOS terminal, but from the kos-scripts repo on your machine).

```bash
make push-action ACTION=blinky TARGET=name-kostest
```

This copies (a minified version of) the file `source/action/blinky.ks` from the `kos-scripts` repository into the actual Ship/Scripts folder inside KSP, and renames it so that the `TARGET` vessel can detect that the update is meant for it. Exactly how this works is in flux, see [Beacon Update File Targeting](#beacon-update-file-targeting).

### Mission Example

A mission `test-airstream` can be pushed to the vessel with uuid `5327904214` with the following command on the host machine (i.e. not in a kOS terminal, but from the kos-scripts repo on your machine).

```bash
make push-mission MISSION=test-airstream TARGET=uuid-5327904214
```

This copies (a minified version of) the file `source/mission/test-airstream.ks` from the `kos-scripts` repository into the actual Ship/Scripts folder inside KSP, and renames it so that the `TARGET` vessel can detect that the update is meant for it. Exactly how this works is in flux, see [Beacon Update File Targeting](#beacon-update-file-targeting).

## Minification

kOS limits the amount of disk space you have available on any given ship, this disk space usage is calculated by doing a character count on all of the files loaded onto the disk. For .ks files this includes comments and all sorts of other unnecessary characters.

This is unfortunate because it discourages at least the following, which are generally good for making software:

1. Discourages detailed comments (or really, any comments at all)
2. Discourages descriptive variable and function names

I don't like working with those restrictions, but can only do so much to work around it. It is possible at least to post-process the .ks files to work within the allowance of the kOS grammar to crunch the source files. That is exactly what the `ksmin.py` script does and there are companion targets in the Makefile to help with it.

Primarily, you will either want to minify a single file (for test purposes):

```bash
make minify-single-file FILE=./source/leolib/lib_bootstrap.ks
```

Or you want to minify all of the files (so you can actually use them):

```base
make minify-all-safe
```

You may be wondering, why not just compile the .ks files into .ksm and I have two responses to that. (1) I am currently doing that and (2) that has *a lot* of overhead. In some cases the .ksm files I am ending up with are actually larger than the .ks files that I started with, and at least in what I have seen so far the .ksm files are always larger than my minified files as well.

Currently, only the minify-all-safe option is safe to use. With the more
aggressive minify-all target some scripts work (those that do not declare
variables or functions), but others do not.

The difference between the safe and non-safe options w.r.t. file size is not
significant enough for the time I need to put into closing the gap, so this is
ok for now.

## Beacon Update File Targeting

**TODO**: I will document this at some point, but I am considering an overhaul to this whole system pretty soon so I don't want to do that just now.

[kerbal-space-programming]: https://www.youtube.com/watch?v=fNlAME5eU3o&list=PLb6UbFXBdbCrvdXVgY_3jp5swtvW24fYv
