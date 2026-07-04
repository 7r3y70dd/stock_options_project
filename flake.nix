{
  description = "Stock options project dev shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python311
          uv

          docker
          postgresql_15
          redis

          gcc
          gnumake
          pkg-config
          openssl
          libffi
          zlib

          git
          curl
          jq
        ];

        shellHook = ''
          export PYTHONPATH="$PWD"
          export ENVIRONMENT=dev
          export DATABASE_URL="postgresql://options_user:options_password@localhost:5432/options_tracker"
          export REDIS_URL="redis://localhost:6379/0"

          echo "Stock options dev shell"
          echo "Python: $(python --version)"
          echo "Use: uv venv .venv && source .venv/bin/activate && uv pip install -r requirements.txt"
        '';
      };
    };
}
