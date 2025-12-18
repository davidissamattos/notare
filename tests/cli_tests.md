# Tests
List of test commands to run on the CLI that executes most of the functionality. 
Useful to get some examples on how to use and how it works

Linux:
```bash
cat tests/data/BrahWiMeSample.musicxml | notare show 
cat tests/data/BrahWiMeSample.musicxml | notare show --print

cat tests/data/MozartPianoSonata.musicxml | notare show 
cat tests/data/MozartPianoSonata.musicxml | notare extract --measures "1-3" | notare show 
cat tests/data/MozartPianoSonata.musicxml | notare extract --measures "1,3" | notare show 
```

Windows cmd:
```bash
type tests\data\BrahWiMeSample.musicxml | notare show 
type tests\data\BrahWiMeSample.musicxml | notare show --print

type tests\data\MozartPianoSonata.musicxml | notare show 
type tests\data\MozartPianoSonata.musicxml | notare extract --measures "1-3" | notare show 
type tests\data\MozartPianoSonata.musicxml | notare extract --measures "1,3" | notare show 
type tests\data\MozartPianoSonata.musicxml | notare extract --part-number 0 | notare show #show all parts
type tests\data\MozartPianoSonata.musicxml | notare extract --part-number 1 | notare show

type tests\data\MozartPianoSonata.musicxml | notare delete --measures "2-3" | notare show
type tests\data\MozartPianoSonata.musicxml | notare delete --part-number 0 | notare show

type tests\data\MozartPianoSonata.musicxml | notare metadata #all metadata
type tests\data\MozartPianoSonata.musicxml | notare metadata --composer
type tests\data\MozartPianoSonata.musicxml | notare metadata --clef --key-signature --composer --title
type tests\data\c_scale.musicxml | notare set-metadata --composer "J. Doe" | notare metadata --composer

type tests\data\MozartPianoSonata.musicxml | notare analyze

# Simplify module
type tests\data\MozartPianoSonata.musicxml | notare simplify --ornament-removal 

# Add module
type tests\data\MozartPianoSonata.musicxml | notare add --to-add tests\data\c_scale_basic.musicxml --measure 4 --before > out_added.musicxml

# Set Part Metadata
type tests\data\MozartPianoSonata.musicxml | notare set-part-metadata --part-number 2 --order 1 > out_reordered.musicxml
type tests\data\MozartPianoSonata.musicxml | notare set-part-metadata --part-name "Piano" --name "Grand Piano" > out_renamed.musicxml

```


Windows Power shell:
```bash
Get-Content tests\data\BrahWiMeSample.musicxml | notare show 
type tests\data\BrahWiMeSample.musicxml | notare show --print
Get-Content  tests\data\MozartPianoSonata.musicxml | notare show 
Get-Content  tests\data\MozartPianoSonata.musicxml | notare extract --measures "1-3" | notare show 
Get-Content  tests\data\MozartPianoSonata.musicxml | notare extract --measures "1,3" | notare show 
Get-Content  tests\data\MozartPianoSonata.musicxml | notare extract --part-number 0 | notare show #show all parts
Get-Content  tests\data\MozartPianoSonata.musicxml | notare extract --part-number 1 | notare show
Get-Content  tests\data\MozartPianoSonata.musicxml | notare delete --measures "2-3" | notare show
Get-Content  tests\data\MozartPianoSonata.musicxml | notare delete --part-number 0 | notare show
Get-Content  tests\data\MozartPianoSonata.musicxml | notare metadata #all metadata
Get-Content  tests\data\MozartPianoSonata.musicxml | notare metadata --composer
Get-Content  tests\data\MozartPianoSonata.musicxml | notare metadata --clef --key-signature --composer --title
Get-Content  tests\data\c_scale.musicxml | notare set-metadata --composer "J. Doe" | notare metadata --composer
Get-Content  tests\data\MozartPianoSonata.musicxml | notare analyze

# Simplify module
Get-Content tests\data\MozartPianoSonata.musicxml | notare simplify --ornament-removal 

# Add module
Get-Content tests\data\MozartPianoSonata.musicxml | notare insert --to-add tests\data\c_scale_basic.musicxml --measure 4 --before > out_added.musicxml

# Set Part Metadata
Get-Content  tests\data\MozartPianoSonata.musicxml | notare set-part-metadata --part-number 2 --order 1 > out_reordered.musicxml
Get-Content  tests\data\MozartPianoSonata.musicxml | notare set-part-metadata --part-name "Piano" --name "Grand Piano" > out_renamed.musicxml

```