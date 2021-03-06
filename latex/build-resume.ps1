$outPath = "./out"
If(!(Test-Path $outPath))
{
    New-Item -ItemType Directory -Force -Path $outPath
}

docker run --rm -it -v ${PWD}:/data rabbitsharp/latex xelatex -output-directory="$outPath" resume.tex
./out/resume.pdf
