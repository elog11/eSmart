#include <linux/limits.h>
#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
	setuid(0);
	char cmd[255];

	if (argc > 1) {
		if (strcmp(argv[1], "start") == 0) {

			sprintf(cmd, "/../esmart_daemon.py");
			system(cmd);

		} else if (strcmp(argv[1], "restart") == 0) {

			sprintf(cmd, "/../esmart_client.py -t");
			system(cmd);
			sprintf(cmd, "/../esmart_daemon.py");
			system(cmd);

		} else if (strcmp(argv[1], "debug") == 0) {

			sprintf(cmd, "/../esmart_client.py -t");
			system(cmd);
			sprintf(cmd, "/../esmart_daemon.py -d");
			system(cmd);

		} else if (strcmp(argv[1], "restore") == 0 && (argc > 2)) {

			char updateScript[255];
			strncpy(updateScript, argv[0], sizeof(updateScript));
			dirname(updateScript);
			sprintf(cmd, "/restore_esmart.sh %s", argv[2]);
			strncat(updateScript, cmd, sizeof(updateScript));
			system(updateScript);

		} else if (strcmp(argv[1], "delete-backup") == 0 && (argc > 2)) {

			sprintf(cmd, "rm -rf /var/eSmart-backups/%s", argv[2]);
			system(cmd);

		} else if (strcmp(argv[1], "backup") == 0) {

			char updateScript[255];
			strncpy(updateScript, argv[0], sizeof(updateScript));
			dirname(updateScript);
			strncat(updateScript, "/update_esmart.sh backup", sizeof(updateScript));
			system(updateScript);

		} else if (strcmp(argv[1], "upgrade") == 0) {

			char updateScript[255];
			strncpy(updateScript, argv[0], sizeof(updateScript));
			dirname(updateScript);
			strncat(updateScript, "/update_esmart.sh upgrade", sizeof(updateScript));
			system(updateScript);

		} else if (strcmp(argv[1], "updatecheck") == 0) {

			char updateScript[255];
			strncpy(updateScript, argv[0], sizeof(updateScript));
			dirname(updateScript);
			strncat(updateScript, "/update_esmart.sh updatecheck", sizeof(updateScript));
			int status;
			if((status = system(updateScript)) != -1) {
                return WEXITSTATUS(status);
        	}

		}
	} else {

		printf("esmart-wrapper: A wrapper to allow the esmart web interface\n");
		printf("                to stop and start the daemon and update the\n");
		printf("                esmart system to the latest version.\n\n");
		printf("Usage: esmart-wrapper start|restart|debug|update|restore [commit]\n\n");
		printf("Options:\n");
		printf("   start:                  Start the esmart daemon\n");
		printf("   restart:                Restart the esmart daemon in normal mode\n");
		printf("   debug:                  Restart the esmart daemon in debug mode\n");
		printf("   backup:                 Create a backup of eSmart\n");
		printf("   delete-backup [folder]: Delete eSmart backup folder named [folder]\n");
		printf("   upgrade:                Upgrade eSmart to the latest version on github\n");
		printf("   restore [commit]:       Restore eSmart to a backed up version\n");
		printf("   updatecheck:            Check for a newer version of eSmart on github\n\n");
	}

	return 0;
}
