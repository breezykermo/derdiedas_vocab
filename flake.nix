{
  description = "Build Anki decks (.apkg) from der|die|das vocabulary JSON";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        pythonEnv = pkgs.python3.withPackages (ps: [
          ps.genanki
        ]);

        derdiedas-to-anki = pkgs.writeShellApplication {
          name = "derdiedas-to-anki";
          runtimeInputs = [ pythonEnv ];
          text = ''
            exec python ${./derdiedas_to_anki.py} "$@"
          '';
        };
      in
      {
        # `nix develop` -> plain `python derdiedas_to_anki.py --vocab vocab/k1.json`
        devShells.default = pkgs.mkShell {
          packages = [ pythonEnv pkgs.curl ];
        };

        # `nix run . -- --vocab vocab/k1.json`
        packages.default = derdiedas-to-anki;
        apps.default = {
          type = "app";
          program = "${derdiedas-to-anki}/bin/derdiedas-to-anki";
        };
      });
}
