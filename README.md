# A simple audio duplicate finder based on Chromaprint

This tries to determine whether any audio files under the given
directories sound the same as each other.

It uses `fpcalc` from [Chromaprint](https://acoustid.org/chromaprint),
and the `gmpy2` Python package.


## Synopsis

On a Debian derivative:

```
sudo apt install libchromaprint-tools python3-gmpy2
git clone
./audio-dupes/find-duplicates this/directory that/directory something.m4a
```

This will compare all the audio files under `this/directory` and
`that/directory`, as well as `something.m4a`. If any sound similar
enough, it will print out a list of those duplicates.


## Options

*  `-t`, `--trim-silence` ignores silence at the beginning of file.

*  `-o REPORT_FILE` prints a copy of its final determinations to the
   named file. This is a exact copy of the last bit of the final
   output

*  `--colour {yes,no,auto}`: use `--colour=yes` to always output ANSI
colour codes, `--colour=no` to never to that. The default (equivalent
to `--colour=auto`) is to use colour when stdout looks like it is
directed to a terminal. (`--color` also works).

*  `-v`, `--verbose`: prints a little bit more.

* `-V`, `--version`: prints a number and exits.

* `-h`, `--help`: summarises this section.


## Missing options

There is no `-q`, `--quiet`, and the default output is quite noisy.
Just use `> /dev/null` or put up with it. The chatter is there so you
know it is working.

It is tempting to have a `--fingerprint-duration` option to change how much
audio is fingerprinted (fpcalc’s default is 120 seconds), and/or
options to change the size of the sliding windows used for comparing
fingerprints, but I don't know if these would be much use in practice.

More useful probably would be an `--ignore-duration` option to not use
the short-cut assumption that tracks that differ by more than one
minute must be different.

Someone will want `--json`.


## What else could I use?

* [Audio Match](https://github.com/unmade/audiomatch) by Aleksei
Maslakov does much the same thing. It makes more effort to participate
in the Python packaging ecosystem, and comes with a Dockerfile.
It is probably a but slower, since it does more of the sliding window
search in Python, while find-duplicates uses `libgmp`. It makes
slightly different assumptions about what a good match looks like, but
this is unlikely to make much difference in practice. Both projects
are based on Chromaprint.

* Roll your own using the
[Chromaprint](https://acoustid.org/chromaprint) library and tools by
Lukáš Lalinský. The results are good, and there really isn't much work
required.


## Bugs and patches

https://gitlab.com/douglasbagnall/find-audio-duplicates is preferred.
https://github.com/douglasbagnall/find-audio-duplicates is there if
you like that one better.


## Design decisions

### Why use `fpcalc` sub-processes and not Chromaprint Python bindings?

Because `fpcalc` uses ffmpeg libraries to parse/decode the files, and
redoing all that work would not be fun. Also:

* The Chromaprint Python bindings look to be less maintained than `fpcalc`.
* The process and output parsing overhead is minuscule compared to the work done.
* This way we don't need to worry about memory leaks.

(My original plan was to use Gstreamer's chromaprint plugin, until I
saw how simple the sub-process call was).


### Why not do the `gmpy2.pack()` once for each fingerprint?

That would save a bit of time, but it got quite fiddly trying to do
the shifting and masking.

### Isn't this transitive clustering thing a bit crappy?

Yes, but it *usually* doesn't matter. What I mean by transitive
clustering is that if A matches B, and B matches C, A is put in a
cluster with C, even though it doesn't match.

In practice this can be a problem when a number of files contain a
sizeable chunk of similar audio (typically, silence), but are not
otherwise similar. Not only will they be clustered together, but any
files that they genuinely resemble will be added to the same cluster.

### How did you pick the various thresholds?

Using a limited amount of trial and error.
