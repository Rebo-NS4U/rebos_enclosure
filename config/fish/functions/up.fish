function up --description 'Go up one directory, or a given number of levels'
    if test (count $argv) -gt 1
        printf 'Usage: up [levels] — for example, up 2\n' >&2
        return 2
    end
    set -l levels 1
    if set -q argv[1]
        set levels $argv[1]
    end
    if not string match -qr '^[1-9][0-9]*$' -- "$levels"
        printf 'up: levels must be a positive whole number\n' >&2
        return 2
    end
    cd -- (string repeat -n $levels '../')
end
